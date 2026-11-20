import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parent.parent


class DoubaoPluginPackagingTest(unittest.TestCase):
    def test_open_platform_plugin_has_connector_and_complete_source_skills(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [str(ROOT / 'scripts/doubao_packaging_v2'), '--output', temporary],
                cwd=temporary, capture_output=True, text=True, check=True,
            )
            manifest = json.loads((ROOT / 'plugin.json').read_text())
            output = Path(temporary) / f"tiana-doubao-plugin-{manifest['version']}.zip"
            self.assertEqual(result.stdout.strip(), str(output))
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                packaged_manifest = json.loads(archive.read('plugin.json'))
                display = packaged_manifest.pop('extensions')['com.doubao']
                self.assertEqual(packaged_manifest, manifest)
                self.assertEqual(display['displayDescription']['zh'],
                                 '一站式开发部署平台，提供代码、数据库、前后端服务、密钥托管等全套能力')
                icon = display['icon'].removeprefix('./')
                self.assertEqual(display['chatIcon'], display['icon'])
                self.assertEqual(display['isMinorIncluded'], 'true')
                self.assertEqual(display['privacyPolicyUrl'], 'https://console.tianacloud.com/docs/terms-of-use')
                icon_content = archive.read(icon)
                self.assertEqual(icon_content, (ROOT / 'packaging/doubao/assets/icon.png').read_bytes())
                self.assertEqual(struct.unpack('>II', icon_content[16:24]), (512, 512))

                connectors = json.loads(archive.read('com.doubao/cli.json'))['connectors']
                self.assertEqual(list(connectors), ['tiana'])
                cli = connectors['tiana']
                self.assertEqual(cli['install']['default'], ['npm install -g @tianacloud/cli@latest'])
                self.assertEqual(cli['install']['win32'], ['npm.cmd install -g @tianacloud/cli@latest'])
                for platform, command in [('default', 'tiana'), ('win32', 'tiana.cmd')]:
                    self.assertEqual(cli['auth'][platform], [f'{command} login --from doubao'])
                    self.assertEqual(cli['status'][platform], [f'{command} status --auth-only --json'])
                    self.assertEqual(cli['versionCheck'][platform], [f'{command} version'])
                    self.assertEqual(cli['unAuth'][platform], [f'{command} logout'])
                    self.assertEqual(cli['help'][platform], [f'{command} help'])
                self.assertRegex('{"data":{"logged_in": true}}', cli['statusMatchRegex'])
                self.assertNotRegex('{"data":{"logged_in":false}}', cli['statusMatchRegex'])

                skill_names = {
                    'tiana': 'tianacloud',
                    'tiana-function': 'tianacloud-function',
                    'tiana-git': 'tianacloud-git',
                    'tiana-sqlite': 'tianacloud-sqlite',
                    'tiana-web': 'tianacloud-web',
                }
                source_files = {
                    f'skills/{skill_names[skill.parent.name]}/{p.relative_to(skill.parent).as_posix()}': p
                    for skill in (ROOT / 'skills').glob('*/SKILL.md')
                    for p in skill.parent.rglob('*')
                    if p.is_file() and not {'__pycache__', '__MACOSX'}.intersection(p.parts)
                    and p.name != '.DS_Store' and not p.name.startswith('._') and p.suffix not in ('.pyc', '.pyo')
                }
                expected_files = [
                    'plugin.json', 'com.doubao/cli.json', icon, 'LICENSE', *source_files,
                ]
                main_skill = archive.read('skills/tianacloud/SKILL.md')
                for alias in list(skill_names.values())[1:]:
                    self.assertIn(f'`{alias}` 技能'.encode(), main_skill)
                git_guide = archive.read('skills/tianacloud-git/references/source-releases.md')
                self.assertIn('`tianacloud` 技能'.encode(), git_guide)
                self.assertIn(b'`git fetch tiana`', git_guide)
                for name, source in source_files.items():
                    actual = archive.read(name)
                    if name.endswith('/SKILL.md'):
                        header, delimiter, body = actual.partition(b'\n---\n')
                        original_name = source.parent.name
                        self.assertIn(f'\nname: {skill_names[original_name]}\n'.encode(), header)
                        self.assertIn(f'/agent-skills/tree/main/skills/{original_name}'.encode(), header)
                        if original_name != 'tiana':
                            self.assertIn(b'\n  parent: tianacloud\n', header)
                            header = header.replace(b'\n  parent: tianacloud\n', b'\n  parent: tiana\n')
                        header = header.replace(f'\nname: {skill_names[original_name]}\n'.encode(),
                                                f'\nname: {original_name}\n'.encode())
                        self.assertIn(b'\n  display_name: "', header)
                        self.assertIn(b'\n  display_description: "', header)
                        path_match = re.search(rb'^  icon: "(\./[^"]+)"$', header, flags=re.M)
                        self.assertIsNotNone(path_match)
                        skill_icon = Path(name).parent / path_match[1].decode()
                        self.assertEqual(archive.read(skill_icon.as_posix()), icon_content)
                        expected_files.append(skill_icon.as_posix())
                        header = re.sub(rb'^  (?:display_name|display_description|icon):.*\n', b'', header, flags=re.M)
                        actual = header + delimiter + body
                    if source.suffix == '.md':
                        actual = actual.replace(b'`tianacloud`', b'`tiana`')
                        actual = actual.replace('使用 tianacloud；'.encode(), '使用 tiana；'.encode())
                        actual = actual.replace(b'tianacloud-', b'tiana-')
                    self.assertEqual(actual, source.read_bytes(), name)
                self.assertCountEqual(archive.namelist(), expected_files)


if __name__ == '__main__':
    unittest.main()
