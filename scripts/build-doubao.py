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

import argparse
import posixpath

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', required=True, type=Path, help='npm pack directory including npm-pack.json')
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--cli-version', required=True)
parser.add_argument('--skills-version', required=True)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parent.parent
SOURCE, OUT = args.source, args.output
CLI, SKILLS = args.cli_version, args.skills_version
if not all(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', v) for v in (CLI, SKILLS)):
    parser.error('CLI and Skills require exact stable versions')
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
    'tiana-function': ('Tiana Function', '创建 Go 后端服务、管理源码、参数及编译发布。'),
    'tiana-secrets': ('Tiana Secrets', '管理用户密钥名称、版本、写入与删除。'),
}
assert {name.split('/')[1] for name in entries} == set(labels)

fixed_check = f'''## 每个会话一次的更新检查

本豆包发行版固定 CLI **{CLI}**、Skills **{SKILLS}**，通过豆包人工接入的分平台包和配套 Skills 交付。
首次使用时执行 `tiana version`，核对结果为 {CLI}，并核对实际加载技能的 metadata.version 为 {SKILLS}。
沿用豆包给出的可执行路径；Windows 文件名为 `tiana.exe`，macOS/Linux 为 `tiana`。
版本不符或命令缺失时，按 Tiana 的开始使用说明修复本发行版安装，再继续资源操作。
升级由接入团队更新对应平台包和配套 Skills，并验证实际版本。核验记录由各个 Tiana 技能共享；后续轮次复用本会话记录。

'''

for name, raw in list(entries.items()):
    if not name.endswith('.md'):
        continue
    text = raw.decode()
    if name.endswith('/SKILL.md'):
        skill = name.split('/')[1]
        label, description = labels[skill]
        text = text.replace('metadata:\n', 'metadata:\n  icon: \"./assets/icon.png\"\n  display_name: ' + json.dumps(label, ensure_ascii=False) + '\n  display_description: ' + json.dumps(description, ensure_ascii=False) + '\n', 1)
        text = re.sub(r'## 每个会话一次的更新检查\n.*?(?=\n## )', fixed_check.rstrip() + '\n', text, flags=re.S)
        if skill == 'tiana-function':
            text = re.sub(r'安装、账号与环境选择按 .*?(?=\n\n## 创建与修改)',
                          f'安装、账号与环境选择按 [Tiana](../tiana/SKILL.md)。先完成该入口的固定版本核验：CLI {CLI}、Skills {SKILLS}。执行前确认 `tiana function --help` 可用；缺少命令时报告实际版本与安装路径，修复豆包平台包安装后再继续。', text, flags=re.S)
        text = text.replace('本技能使用 `@tianacloud/cli`，包内提供 `tiana` 和 `git-remote-tiana`。',
                            '本技能使用豆包分平台包提供的原生 `tiana`。需要原生 Git 时，按 [Git helper 准备](references/windows-git-helper.md)建立入口。')
        text = text.replace('使用原生 Git 和包内的 `git-remote-tiana`。',
                            '使用原生 Git，并按 [Git helper 准备](../tiana/references/windows-git-helper.md)建立 `git-remote-tiana` 入口。')
    entries[name] = text.encode()


def render(text):
    return text.replace('{{CLI_VERSION}}', CLI).replace('{{SKILLS_VERSION}}', SKILLS).replace('{{SKILL_COUNT}}', str(len(labels)))

for template in (ROOT / 'packaging/doubao/references').glob('*.md'):
    entries['skills/tiana/references/' + template.name] = render(template.read_text()).encode()
source_path = 'skills/tiana-git/references/source-releases.md'
text = entries[source_path].decode()
text = re.sub(r'在 Agent 实际执行命令的环境中检查 .*?(?=\n\n)',
              '在 Agent 实际执行命令的环境中检查 `git --version`、`tiana version` 及 `git-remote-tiana` 的命令路径。CLI 使用豆包分平台包提供的原生文件；按 [Git helper 准备](../../tiana/references/windows-git-helper.md)建立并核验入口，随后继续源码操作。', text, count=1, flags=re.S)
entries[source_path] = text.encode()
name = 'skills/tiana/references/cloud-cli.md'
text = entries[name].decode()
pos = text.index('\n')
text = text[:pos+1] + '\n豆包连接器授权由宿主运行阻塞式 `tiana login`，随后独立检查本地登录态，流程见 [开始使用](getting-started.md#对话中的登录)。本文列出的分步登录参数用于 CLI 手动调用参考。\n' + text[pos+1:]
entries[name] = text.encode()
icon = (ROOT / 'packaging/doubao/assets/icon.png').read_bytes()
for skill in labels:
    entries[f'skills/{skill}/assets/icon.png'] = icon
entries = {name.removeprefix('skills/'): value for name, value in entries.items()}
entries['LICENSE'] = source_skills['LICENSE']
for name, raw in entries.items():
    if not name.endswith('.md'):
        continue
    text = raw.decode()
    assert not re.search(r'WorkBuddy|latest|tianacloud-staging', text, re.I), name
    for link in re.findall(r'\]\(([^)]+)\)', text):
        target = link.split('#')[0]
        if target and '://' not in target:
            assert posixpath.normpath(posixpath.join(posixpath.dirname(name), target)) in entries, (name, target)
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
(OUT / 'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'SHA256SUMS'))
print(OUT)
print(f'Verified 5 platform ZIPs and {len(labels)} Skills, CLI {CLI}, Skills {SKILLS}')
