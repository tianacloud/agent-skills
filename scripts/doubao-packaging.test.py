import base64
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parent.parent


class DoubaoPackagingTest(unittest.TestCase):
    def test_pinned_packages_produce_native_zips_and_complete_source_skills(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'source'
            output = Path(temporary) / 'output'
            source.mkdir()
            descriptors = []

            def package(name, version, files):
                filename = name.removeprefix('@').replace('/', '-') + f'-{version}.tgz'
                with tarfile.open(source / filename, 'w:gz') as archive:
                    for path, data in files.items():
                        info = tarfile.TarInfo('package/' + path)
                        info.size = len(data)
                        archive.addfile(info, io.BytesIO(data))
                digest = base64.b64encode(hashlib.sha512((source / filename).read_bytes()).digest()).decode()
                descriptors.append(dict(name=name, version=version, filename=filename, integrity='sha512-' + digest))

            cli_version = '1.2.3'
            skills_version = json.loads((ROOT / 'package.json').read_text())['version']
            platforms = [
                ('linux', 'x64', 'linux_amd64'), ('linux', 'arm64', 'linux_arm64'),
                ('darwin', 'x64', 'darwin_amd64'), ('darwin', 'arm64', 'darwin_arm64'),
                ('win32', 'x64', 'windows_amd64'),
            ]
            for os_name, cpu, _ in platforms:
                binary = 'tiana.exe' if os_name == 'win32' else 'tiana'
                package(f'@tianacloud/cli-{os_name}-{cpu}', cli_version, {
                    'package.json': json.dumps(dict(version=cli_version, os=[os_name], cpu=[cpu])).encode(),
                    f'bin/{binary}': f'native fixture: {os_name}/{cpu}'.encode(),
                })
            skills = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'skills').rglob('*')
                      if p.is_file() and p.name != '.npmignore' and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
            package('@tianacloud/agent-skills', skills_version, {
                **skills, 'LICENSE': (ROOT / 'LICENSE').read_bytes(),
                'package.json': json.dumps(dict(version=skills_version)).encode(),
            })
            (source / 'npm-pack.json').write_text(json.dumps(descriptors))
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/build-doubao.py'),
                                     '--source', str(source), '--output', str(output),
                                     '--cli-version', cli_version, '--skills-version', skills_version],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(output / f'tiana-skills-{skills_version}.zip') as archive:
                self.assertEqual({n.split('/')[0] for n in archive.namelist()} - {'LICENSE'},
                                 {'tiana', 'tiana-web', 'tiana-git', 'tiana-sqlite', 'tiana-function'})
                for name, original in skills.items():
                    actual = archive.read(name.removeprefix('skills/'))
                    if name.endswith('/SKILL.md'):
                        actual = re.sub(rb'^  (?:display_name|display_description|icon):.*\n', b'', actual, flags=re.M)
                    self.assertEqual(actual, original, name)
                for skill in ['tiana', 'tiana-web', 'tiana-git', 'tiana-sqlite', 'tiana-function']:
                    self.assertEqual(archive.read(f'{skill}/assets/icon.png'),
                                     (ROOT / 'packaging/doubao/assets/icon.png').read_bytes())
                    frontmatter = archive.read(f'{skill}/SKILL.md').decode().split('\n---\n', 1)[0]
                    for field in ['display_name', 'display_description', 'icon']:
                        self.assertIn(f'\n  {field}:', frontmatter)
            for os_name, cpu, suffix in platforms:
                with zipfile.ZipFile(output / f'tiana_{suffix}.zip') as archive:
                    binary = 'tiana.exe' if os_name == 'win32' else 'tiana'
                    self.assertEqual(archive.namelist(), [binary])
                    self.assertEqual(archive.read(binary), f'native fixture: {os_name}/{cpu}'.encode())
                    self.assertEqual((archive.getinfo(binary).external_attr >> 16) & 0o777, 0o755)
            self.assertTrue((output / 'CLI-接入配置与技术手册.md').is_file())
            self.assertTrue((output / 'TEST-RESULTS.md').is_file())
            for line in (output / 'SHA256SUMS').read_text().splitlines():
                digest, name = line.split('  ', 1)
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)
            delivery_name = f'tiana-doubao-manual-skills-{skills_version}-cli-{cli_version}'
            delivery = output.parent / f'{delivery_name}.zip'
            self.assertTrue(delivery.is_file())
            with zipfile.ZipFile(delivery) as archive:
                self.assertIsNone(archive.testzip())
                files = {name: archive.read(name) for name in archive.namelist()}
            self.assertEqual(files, {f'{delivery_name}/{p.name}': p.read_bytes() for p in output.iterdir()})
            self.assertEqual(Path(str(delivery) + '.sha256').read_text(),
                             f'{hashlib.sha256(delivery.read_bytes()).hexdigest()}  {delivery.name}\n')
            self.assertEqual(result.stdout.splitlines()[-1], str(delivery.resolve()))


if __name__ == '__main__':
    unittest.main()
