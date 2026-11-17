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
    def test_channel_binaries_and_complete_published_skills(self):
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
            cli_source = Path(temporary) / 'cli'
            (cli_source / 'cmd/tiana').mkdir(parents=True)
            (cli_source / 'cmd/tiana-qwenwork').mkdir(parents=True)
            (cli_source / 'internal/buildconfig').mkdir(parents=True)
            (cli_source / 'go.mod').write_text('module github.com/tianacloud/cli\n\ngo 1.25.0\n')
            (cli_source / 'LICENSE').write_bytes(b'CLI license')
            (cli_source / 'internal/buildconfig/config.go').write_text('package buildconfig\nvar DefaultAcquisitionSource string\n')
            (cli_source / 'cmd/tiana/main.go').write_text('package main\nimport ("fmt"; "github.com/tianacloud/cli/internal/buildconfig")\nvar version string\nfunc main() { fmt.Println(version, buildconfig.DefaultAcquisitionSource) }\n')
            (cli_source / 'cmd/tiana-qwenwork/main.go').write_text('package main\nimport "fmt"\nfunc main() { fmt.Println("adapter") }\n')
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
                                     '--source', str(source), '--output', str(output), '--cli-source', str(cli_source),
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
                self.assertEqual({name for name in archive.namelist() if name.startswith('skills/')}, set(skills))
                review = ROOT / 'packaging/qwen/review'
                review_files = [path for path in review.rglob('*') if path.is_file()]
                self.assertTrue(review_files)
                self.assertEqual(
                    {name for name in archive.namelist() if name.startswith('review/')},
                    {'review/' + path.relative_to(review).as_posix() for path in review_files})
                for path in review_files:
                    expected = path.read_bytes()
                    if path.suffix == '.md':
                        expected = expected.replace(b'{{CLI_VERSION}}', b'2.3.4').replace(
                            b'{{SKILLS_VERSION}}', b'5.6.7')
                    name = 'review/' + path.relative_to(review).as_posix()
                    self.assertEqual(archive.read(name), expected, name)
                    self.assertEqual((archive.getinfo(name).external_attr >> 16) & 0o777, 0o644)
                for os_name, cpu, directory, binary in platforms:
                    name = f'bin/{directory}/{binary}'
                    self.assertGreater(len(archive.read(name)), 1000)
                    core = Path(temporary) / binary
                    core.write_bytes(archive.read(f'bin/{directory}/libexec/{binary}'))
                    metadata = subprocess.check_output(['go', 'version', '-m', str(core)], text=True)
                    self.assertIn(b'qwenwork', core.read_bytes())
                    self.assertIn(b'2.3.4', core.read_bytes())
                    self.assertIn('GOOS=' + directory.split('_')[0], metadata)
                    self.assertIn('GOARCH=' + directory.split('_')[1], metadata)
                    self.assertEqual((archive.getinfo(name).external_attr >> 16) & 0o777, 0o755)
                self.assertEqual(archive.read('LICENSE'), b'Skills license')
                self.assertEqual(archive.read('licenses/cli-LICENSE'), b'CLI license')
            build = json.loads(delivery.with_suffix('.build.json').read_text())
            self.assertEqual(build['cli_source']['default_acquisition_source'], 'qwenwork')
            digest = hashlib.sha256(delivery.read_bytes()).hexdigest()
            self.assertEqual(Path(str(delivery) + '.sha256').read_text(), f'{digest}  {delivery.name}\n')


if __name__ == '__main__':
    unittest.main()
