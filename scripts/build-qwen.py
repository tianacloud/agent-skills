#!/usr/bin/env python3
"""Build channel-specific native CLI binaries and package Skills for QwenWork desktop."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import tarfile
import tempfile
import zipfile


from channel_build import build_binary, resolve_source

ACQUISITION_SOURCE = 'qwenwork'

ROOT = Path(__file__).resolve().parent.parent
PLATFORMS = (
    ('windows_amd64', 'tiana.exe'),
    ('darwin_arm64', 'tiana'),
    ('darwin_amd64', 'tiana'),
)


def build(source, output, cli_version, skills_version, cli_source, source_info):
    records = json.loads((source / 'npm-pack.json').read_text())

    def read_package(name, version):
        record = next(r for r in records if r['name'] == name and r['version'] == version)
        path = source / record['filename']
        algorithm, expected = record['integrity'].split('-', 1)
        actual = base64.b64encode(hashlib.new(algorithm, path.read_bytes()).digest()).decode()
        assert actual == expected, f'{name}: npm integrity mismatch'
        with tarfile.open(path) as archive:
            files = {m.name.removeprefix('package/'): (archive.extractfile(m).read(), m.mode)
                     for m in archive.getmembers() if m.isfile()}
        assert json.loads(files['package.json'][0])['version'] == version, name
        return files

    entries = {}
    for directory, binary in PLATFORMS:
        goos, goarch = directory.split('_')
        entries[f'bin/{directory}/{binary}'] = (
            build_binary(cli_source, cli_version, ACQUISITION_SOURCE, goos, goarch, 'tiana-qwenwork'), 0o755)
        entries[f'bin/{directory}/libexec/{binary}'] = (
            build_binary(cli_source, cli_version, ACQUISITION_SOURCE, goos, goarch), 0o755)
    entries['licenses/cli-LICENSE'] = ((cli_source / 'LICENSE').read_bytes(), 0o644)

    skills = read_package('@tianacloud/agent-skills', skills_version)
    entries.update({name: value for name, value in skills.items() if name.startswith('skills/')})
    skill_paths = sorted(name for name in entries
                         if len(name.split('/')) == 3 and name.endswith('/SKILL.md'))
    assert skill_paths, 'Skills package contains no SKILL.md'
    manifest = {
        'name': 'tiana', 'version': skills_version,
        'description': 'Tiana Cloud account, SQLite, Git, Functions and Web application workflows',
        'author': {'name': '成都沃德天娜科技有限公司'},
        'skills': skill_paths,
    }
    entries['.qwenwork-plugin/plugin.json'] = ((json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode(), 0o644)
    entries['LICENSE'] = (skills['LICENSE'][0], 0o644)
    readme = (ROOT / 'packaging/qwen/README.md').read_text()
    readme = readme.replace('{{CLI_VERSION}}', cli_version).replace('{{SKILLS_VERSION}}', skills_version)
    entries['README.md'] = (readme.encode(), 0o644)
    review = ROOT / 'packaging/qwen/review'
    for path in sorted(review.rglob('*')):
        if path.is_file():
            data = path.read_bytes()
            if path.suffix == '.md':
                data = data.replace(b'{{CLI_VERSION}}', cli_version.encode()).replace(
                    b'{{SKILLS_VERSION}}', skills_version.encode())
            entries['review/' + path.relative_to(review).as_posix()] = (data, 0o644)
    assert len(entries) <= 2048, 'Qwen ZIP entry limit exceeded'
    assert sum(len(data) for data, _ in entries.values()) <= 512 * 1024 * 1024, 'Qwen unpacked size limit exceeded'

    output.mkdir(parents=True, exist_ok=True)
    target = output / f'tiana-qwen-desktop-skills-{skills_version}-cli-{cli_version}.zip'
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, (data, mode) in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 2, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | (mode & 0o777)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)
    assert target.stat().st_size <= 50 * 1024 * 1024, 'Qwen ZIP size limit exceeded'
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name, (data, _) in entries.items():
            assert archive.read(name) == data, name
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    Path(str(target) + '.sha256').write_text(f'{digest}  {target.name}\n')
    target.with_suffix('.build.json').write_text(json.dumps({
        'cli_version': cli_version, 'skills_version': skills_version,
        'connector_version': skills_version, 'platforms': [p[0] for p in PLATFORMS],
        'skills': skill_paths, 'source_integrities': records,
        'cli_source': {**source_info, 'default_acquisition_source': ACQUISITION_SOURCE},
        'sha256': digest, 'bytes': target.stat().st_size,
    }, ensure_ascii=False, indent=2) + '\n')
    print(f'Verified 3 platforms and {len(skill_paths)} Skills; CLI {cli_version}, Skills {skills_version}.')
    print('Package checks only; QwenWork client installation and authentication require separate acceptance.')
    print(target.resolve())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='reuse npm packs with npm-pack.json; otherwise download exact versions')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/qwen')
    parser.add_argument('--cli-source', type=Path, help='local CLI source for build verification')
    parser.add_argument('--cli-version', required=True)
    parser.add_argument('--skills-version', required=True)
    args = parser.parse_args()
    if not all(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', v) for v in (args.cli_version, args.skills_version)):
        parser.error('CLI and Skills require exact stable versions')
    with tempfile.TemporaryDirectory(prefix='tiana-qwen-source-') as temporary:
        source = args.source or Path(temporary)
        if args.source is None:
            packages = [f'@tianacloud/agent-skills@{args.skills_version}']
            print(f'Downloading CLI {args.cli_version} / Skills {args.skills_version}', flush=True)
            result = subprocess.run(['npm', 'pack', '--json', '--ignore-scripts',
                                     '--registry=https://registry.npmjs.org/', '--pack-destination', str(source),
                                     *packages], check=True, stdout=subprocess.PIPE, text=True)
            (source / 'npm-pack.json').write_text(result.stdout)
        cli_source, source_info = resolve_source(args.cli_version, args.cli_source)
        build(source, args.output, args.cli_version, args.skills_version, cli_source, source_info)


if __name__ == '__main__':
    main()
