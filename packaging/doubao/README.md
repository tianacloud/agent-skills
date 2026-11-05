# 豆包 CLI 人工接入打包

按[完整接入指南](https://bytedance.larkoffice.com/docx/J5o2dZK8hoJItxxNQyocHgRzncb)第 4.2 节的 CLI 专项人工接入流程，交付问卷字段、五个平台 ZIP 和配套 Skills。问卷与命令配置维护在 [manual.md](manual.md)。

平台 ZIP 根目录只有一个执行文件：Linux/macOS 为 tiana，Windows 为 tiana.exe；文件名与接入配置入口一致。配套 Skills ZIP 包含五个顶层技能，用户密钥管理位于 tiana-function 内。每个顶层技能目录包含 SKILL.md、资料和 512×512 图标。技能之间按名称衔接任务及结果，文件链接只引用当前技能目录内的资料。

## 构建

需要 Python 3，以及用 npm pack --json 取得的五个平台包和 agent-skills 包。把 npm pack 的 JSON 数组保存为同目录 npm-pack.json；构建检查 SHA512、版本和平台信息。CLI 与 Skills 版本必须为明确的固定正式版本。

```sh
npm run build:doubao -- --source /path/to/npm-packs --output dist/doubao --cli-version 1.0.12 --skills-version 1.0.16
```

业务技能取固定 npm 发行版，豆包副本补充展示元数据、原生初始安装和 Git helper 指引，更新流程取自该 npm 发行版的正式 Skills。通用 skills/ 和 WorkBuddy 的 cli.json 保持各自行为。展示元数据和安装模板只在生成豆包副本时生效。

输出附带平台入口、文件大小和摘要清单，以及配置填写单。发布者补充本次实际执行的 TEST-RESULTS.md，更新 SHA256SUMS，再提供交付压缩包。

## 授权验证

宿主运行 tiana login，等待兑换和保存成功退出后，单独执行 tiana status --auth-only --json；退出码为 0 且 logged_in 为 true 才确认登录。原始正则及 Windows 带 .exe 的命令见手册。

```sh
TIANA_TEST_CLI_BINARY=/absolute/path/to/tiana npm run test:doubao-auth
TIANA_TEST_CLI_BINARY=/absolute/path/to/tiana npm run test:connector-auth
npm run validate:ci
```

认证 fixture 使用真实 CLI 子进程、隔离存储和回环模拟服务；不等同于豆包或 WorkBuddy 桌面验收。每次交付保留平台运行、权限、源二进制一致性及目标客户端待联调项。
