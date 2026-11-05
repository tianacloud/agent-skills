#!/usr/bin/env python3
"""Repackage pinned published artifacts for Doubao's native-package mode."""
import base64
import hashlib
import json
from pathlib import Path
import re
import stat
import tarfile
import zipfile
import subprocess
import tempfile

import argparse
import posixpath

ROOT = Path(__file__).resolve().parent.parent


def build(SOURCE, OUT, CLI, SKILLS):
    OUT.mkdir(parents=True, exist_ok=True)
    pack_info = json.loads((SOURCE / 'npm-pack.json').read_text())
    for pkg in pack_info:
        raw = (SOURCE / pkg['filename']).read_bytes()
        assert pkg['integrity'] == 'sha512-' + base64.b64encode(hashlib.sha512(raw).digest()).decode(), pkg['name']

    def read_package(filename):
        with tarfile.open(SOURCE / filename) as archive:
            return {m.name.removeprefix('package/'): archive.extractfile(m).read()
                    for m in archive.getmembers() if m.isfile()}

    def write_zip(filename, entries, executable=False):
        with zipfile.ZipFile(OUT / filename, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, content in sorted(entries.items()):
                info = zipfile.ZipInfo(name, (2026, 11, 2, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, content, compresslevel=9)

    platforms = [
        ('linux-amd64', 'linux-x64', 'linux', 'x64'),
        ('linux-arm64', 'linux-arm64', 'linux', 'arm64'),
        ('darwin-amd64', 'darwin-x64', 'darwin', 'x64'),
        ('darwin-arm64', 'darwin-arm64', 'darwin', 'arm64'),
        ('windows-amd64', 'win32-x64', 'win32', 'x64'),
    ]
    items = []
    for platform, suffix, os_name, arch in platforms:
        source_name = f'tianacloud-cli-{suffix}-{CLI}.tgz'
        files = read_package(source_name)
        meta = json.loads(files['package.json'])
        assert meta['version'] == CLI and meta['os'] == [os_name] and meta['cpu'] == [arch]
        executable = 'tiana.exe' if os_name == 'win32' else 'tiana'
        binary = files[f'bin/{executable}']
        filename = f'tiana_{platform.replace("-", "_")}.zip'
        write_zip(filename, {executable: binary}, executable=True)
        raw = (OUT / filename).read_bytes()
        items.append(dict(platform=platform, file_name=filename, exec_name=executable,
                          file_size=len(raw), md5=hashlib.md5(raw).hexdigest(),
                          sha256=hashlib.sha256(raw).hexdigest(),
                          binary_sha256=hashlib.sha256(binary).hexdigest(), source=source_name))

    source_skills = read_package(f'tianacloud-agent-skills-{SKILLS}.tgz')
    assert json.loads(source_skills['package.json'])['version'] == SKILLS
    entries = {name: value for name, value in source_skills.items() if name.startswith('skills/')}
    labels = {
        'tiana': ('Tiana Cloud', '账号登录、CLI 使用及实例管理。'),
        'tiana-sqlite': ('Tiana SQLite', '管理云端数据库、SQL 与数据库分支。'),
        'tiana-git': ('Tiana Git', '管理 Git 仓库、同步源码与应用版本。'),
        'tiana-web': ('Tiana Web', '让 AI 创建、修改和部署 Web 应用。'),
        'tiana-function': ('Tiana Function', '创建 Go 后端服务、管理源码、参数、用户密钥及编译发布。'),
    }
    assert {name.split('/')[1] for name in entries} == set(labels)

    for name, raw in list(entries.items()):
        if not name.endswith('.md'):
            continue
        text = raw.decode()
        if name.endswith('/SKILL.md'):
            skill = name.split('/')[1]
            label, description = labels[skill]
            text = text.replace('metadata:\n', 'metadata:\n  icon: \"./assets/icon.png\"\n  display_name: ' + json.dumps(label, ensure_ascii=False) + '\n  display_description: ' + json.dumps(description, ensure_ascii=False) + '\n', 1)
        entries[name] = text.encode()

    def render(text):
        return text.replace('{{CLI_VERSION}}', CLI).replace('{{SKILLS_VERSION}}', SKILLS).replace('{{SKILL_COUNT}}', str(len(labels)))

    icon = (ROOT / 'packaging/doubao/assets/icon.png').read_bytes()
    for skill in labels:
        entries[f'skills/{skill}/assets/icon.png'] = icon
    entries = {name.removeprefix('skills/'): value for name, value in entries.items()}
    entries['LICENSE'] = source_skills['LICENSE']
    for name, raw in entries.items():
        if not name.endswith('.md'):
            continue
        text = raw.decode()
        for link in re.findall(r'\]\(([^)]+)\)', text):
            target = link.split('#')[0]
            if target and '://' not in target:
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
                assert resolved.startswith(name.split('/')[0] + '/'), (name, target, 'outside skill directory')
                assert resolved in entries, (name, target)
        if name.endswith('/SKILL.md'):
            assert f'version: "{SKILLS}"' in text
            for key in ['display_name:', 'display_description:', 'icon:']:
                assert key in text
    skills_file = f'tiana-skills-{SKILLS}.zip'
    write_zip(skills_file, entries)
    (OUT / 'CLI-接入配置与技术手册.md').write_text(render((ROOT / 'packaging/doubao/manual.md').read_text()))
    (OUT / 'packages.json').write_text(json.dumps(dict(cli_version=CLI, skills_version=SKILLS, skills=list(labels), packages=items), ensure_ascii=False, indent=2) + '\n')
    (OUT / 'source-integrities.json').write_text(json.dumps(pack_info, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'README.md').write_text(f"""# TianaCloud 豆包 CLI 人工接入材料

固定 CLI {CLI} / Skills {SKILLS}。

1. 提交 CLI-接入配置与技术手册.md 中的问卷字段与命令配置。
2. 分平台提交五个 tiana_<os>_<arch>.zip，根目录仅一个可执行文件；Linux/macOS 为 tiana，Windows 为 tiana.exe。
3. 提供 {skills_file}，包含 {len(labels)} 个技能、引用资料及各自图标，由豆包接入团队加载。
4. packages.json 为附件清单。源 npm 包完整性见 source-integrities.json；附件摘要见 SHA256SUMS。运行与联调范围见 TEST-RESULTS.md。

依据：https://bytedance.larkoffice.com/docx/J5o2dZK8hoJItxxNQyocHgRzncb 第 4.2 节（已核对 revision 1369）。本材料用于已在对接的 CLI 人工配置流程。
""")
    for item in items:
        with zipfile.ZipFile(OUT / item['file_name']) as archive:
            assert archive.namelist() == [item['exec_name']]
            assert archive.testzip() is None
            assert hashlib.sha256(archive.read(item['exec_name'])).hexdigest() == item['binary_sha256']
    (OUT / 'TEST-RESULTS.md').write_text(f"""# 打包检查结果

CLI {CLI} / Skills {SKILLS}。

- 已校验输入 npm 包 SHA-512、版本及 CLI 平台信息。
- 已校验五个平台 ZIP 的唯一根目录入口、CRC 和源二进制 SHA-256；Linux/macOS 执行权限为 0755。
- 已校验五个技能目录、展示字段、版本及本技能内的 Markdown 文件引用。
- 技能来自指定 npm 正式版，仅补充展示元数据及图标；业务正文、参考资料及脚本保持来源内容。
- 附件摘要见 SHA256SUMS。

本脚本不执行 CLI、不登录账号。各操作系统运行、授权和豆包客户端验收未由本次打包执行。
""")
    (OUT / 'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'SHA256SUMS'))
    print(OUT)
    print(f'Verified 5 platform ZIPs and {len(labels)} Skills, CLI {CLI}, Skills {SKILLS}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='reuse npm packs with npm-pack.json; otherwise download exact versions')
    parser.add_argument('--output', type=Path, help='output directory (default: dist/doubao/cli-VERSION-skills-VERSION)')
    parser.add_argument('--cli-version', required=True)
    parser.add_argument('--skills-version', required=True)
    args = parser.parse_args()
    if not all(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', v) for v in (args.cli_version, args.skills_version)):
        parser.error('CLI and Skills require exact stable versions')
    output = args.output or ROOT / 'dist/doubao' / f'cli-{args.cli_version}-skills-{args.skills_version}'
    with tempfile.TemporaryDirectory(prefix='tiana-doubao-source-') as temporary:
        source = args.source or Path(temporary)
        if args.source is None:
            packages = [f'@tianacloud/cli-{platform}@{args.cli_version}' for platform in
                        ['linux-x64', 'linux-arm64', 'darwin-x64', 'darwin-arm64', 'win32-x64']]
            packages.append(f'@tianacloud/agent-skills@{args.skills_version}')
            print(f'Downloading CLI {args.cli_version} / Skills {args.skills_version}', flush=True)
            result = subprocess.run(['npm', 'pack', '--json', '--ignore-scripts',
                                     '--registry=https://registry.npmjs.org/', '--pack-destination', str(source),
                                     *packages], check=True, stdout=subprocess.PIPE, text=True)
            (source / 'npm-pack.json').write_text(result.stdout)
        build(source, output, args.cli_version, args.skills_version)


if __name__ == '__main__':
    main()
