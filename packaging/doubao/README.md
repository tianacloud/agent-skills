# 豆包 CLI 人工接入打包

按[完整接入指南](https://bytedance.larkoffice.com/docx/J5o2dZK8hoJItxxNQyocHgRzncb)第 4.2 节的 CLI 专项人工接入流程，交付问卷字段、五个平台 ZIP 和配套 Skills。问卷与命令配置维护在 [manual.md](manual.md)。

平台 ZIP 根目录只有一个执行文件：Linux/macOS 为 tiana，Windows 为 tiana.exe；文件名与接入配置入口一致。配套 Skills ZIP 包含五个顶层技能，用户密钥管理位于 tiana-function 内。每个顶层技能目录包含 SKILL.md、资料和 512×512 图标。技能之间按名称衔接任务及结果，文件链接只引用当前技能目录内的资料。

## 构建

在仓库中直接执行，无需传参数（构建机器需有 Python 3 和 npm）：

```sh
./scripts/doubao_packaging
```

脚本查询 CLI、Skills 当前正式版本，确定具体版本号后下载五个平台包和 agent-skills 包，校验 SHA512、版本和平台信息。打包输入是解析后的固定版本号；输出目录为 `dist/doubao/cli-<CLI版本>-skills-<Skills版本>/`。

技能使用指定 npm 正式版的完整业务内容，仅增加豆包要求的展示元数据和图标。固定的是交付版本，技能内的安装、登录与更新指令保持原样。

最终交付文件为 `dist/doubao/tiana-doubao-manual-skills-<Skills版本>-cli-<CLI版本>.zip`，旁边附 `.sha256` 文件。沿用原交付的同名顶层目录，脚本最后一行输出整包的绝对路径。

整包内包含五个平台 ZIP、一个五技能 ZIP、`CLI-接入配置与技术手册.md`、`packages.json`、`source-integrities.json`、`README.md`、`TEST-RESULTS.md` 和 `SHA256SUMS`。测试结果文件只记录脚本实际完成的静态打包检查；客户端运行与授权需另行验收。

## 授权验证

宿主运行 tiana login，等待兑换和保存成功退出后，单独执行 tiana status --auth-only --json；退出码为 0 且 logged_in 为 true 才确认登录。原始正则及 Windows 带 .exe 的命令见手册。

```sh
TIANA_TEST_CLI_BINARY=/absolute/path/to/tiana npm run test:doubao-auth
TIANA_TEST_CLI_BINARY=/absolute/path/to/tiana npm run test:connector-auth
npm run validate:ci
```

认证 fixture 使用真实 CLI 子进程、隔离存储和回环模拟服务；不等同于豆包或 WorkBuddy 桌面验收。每次交付保留平台运行、权限、源二进制一致性及目标客户端待联调项。
