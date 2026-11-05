import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parent.parent


class QwenPackagingTest(unittest.TestCase):
    def test_published_skills_and_platform_binaries_survive_packaging(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'source'
            source.mkdir()
            output = Path(temporary) / 'output'
            records = []

            def package(name, version, files):
                filename = name.removeprefix('@').replace('/', '-') + f'-{version}.tgz'
                with tarfile.open(source / filename, 'w:gz') as archive:
                    for path, content in files.items():
                        info = tarfile.TarInfo('package/' + path)
                        info.size = len(content)
                        info.mode = 0o755 if path.startswith('bin/') else 0o644
                        archive.addfile(info, io.BytesIO(content))
                integrity = 'sha512-' + base64.b64encode(hashlib.sha512((source / filename).read_bytes()).digest()).decode()
                records.append(dict(name=name, version=version, filename=filename, integrity=integrity))

            platforms = [('win32', 'x64', 'windows_amd64', 'tiana.exe'),
                         ('darwin', 'arm64', 'darwin_arm64', 'tiana'),
                         ('darwin', 'x64', 'darwin_amd64', 'tiana')]
            for os_name, cpu, _, binary in platforms:
                package(f'@tianacloud/cli-{os_name}-{cpu}', '2.3.4', {
                    'package.json': json.dumps(dict(version='2.3.4', os=[os_name], cpu=[cpu])).encode(),
                    f'bin/{binary}': f'native {os_name}/{cpu}'.encode(),
                    'LICENSE': b'CLI license',
                })
            skills = {
                'skills/tiana/SKILL.md': b'---\nname: tiana\nmetadata:\n  version: "5.6.7"\n---\nOriginal instructions\n',
                'skills/tiana/references/start.md': b'Published reference\n',
                'skills/new-product/SKILL.md': b'---\nname: new-product\nmetadata:\n  version: "5.6.7"\n---\nNew skill\n',
                'skills/new-product/scripts/action.py': b'print("original")\n',
            }
            package('@tianacloud/agent-skills', '5.6.7', {
                **skills, 'package.json': b'{"version":"5.6.7"}', 'LICENSE': b'Skills license',
            })
            (source / 'npm-pack.json').write_text(json.dumps(records))
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/build-qwen.py'),
                                     '--source', str(source), '--output', str(output),
                                     '--cli-version', '2.3.4', '--skills-version', '5.6.7'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            delivery = Path(result.stdout.splitlines()[-1])
            self.assertTrue(delivery.is_absolute())
            with zipfile.ZipFile(delivery) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read('.qwenwork-plugin/plugin.json'))
                self.assertEqual(manifest['version'], '5.6.7')
                self.assertEqual(set(manifest['skills']), {'skills/tiana/SKILL.md', 'skills/new-product/SKILL.md'})
                for name, content in skills.items():
                    self.assertEqual(archive.read(name), content, name)
                for os_name, cpu, directory, binary in platforms:
                    name = f'bin/{directory}/{binary}'
                    self.assertEqual(archive.read(name), f'native {os_name}/{cpu}'.encode())
                    self.assertEqual((archive.getinfo(name).external_attr >> 16) & 0o777, 0o755)
                self.assertEqual(archive.read('LICENSE'), b'Skills license')
                self.assertEqual(archive.read('licenses/cli-LICENSE'), b'CLI license')
            digest = hashlib.sha256(delivery.read_bytes()).hexdigest()
            self.assertEqual(Path(str(delivery) + '.sha256').read_text(), f'{digest}  {delivery.name}\n')


if __name__ == '__main__':
    unittest.main()
