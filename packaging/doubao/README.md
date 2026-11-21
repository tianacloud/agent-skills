# 豆包打包

## 开放平台 Plugin

在仓库根目录使用 Python 3 打包：

```sh
./scripts/doubao_packaging_v2
```

脚本从当前检出读取版本和 Skills，生成 `dist/doubao/tiana-doubao-plugin-<版本>.zip`，并输出 ZIP 的绝对路径。可以用 `--output <目录>` 指定输出目录。ZIP 根目录包含 `plugin.json`、`com.doubao/cli.json`、展示和会话图标、许可证及五个完整 Skill 目录。各 Skill 保留正文、引用、脚本和资源，打包时补充展示名称、简介及图标。

豆包客户端通过 npm 安装正式版 CLI。登录命令传入 `--from doubao`，状态检查读取 `tiana status --auth-only --json` 输出中的 `logged_in`。

脚本默认将 [Tiana 指定的政策地址](https://console.tianacloud.com/docs/terms-of-use)写入 `privacyPolicyUrl`。如地址变更，可通过 `--privacy-policy-url` 指定新的 HTTPS 地址。上传 ZIP 时，提交版本应与 `plugin.json` 一致。使用 Doubao Dev CLI 上传时，先解压到插件项目目录，再执行 `dbx upload --cwd <插件项目目录>`。后续上传同一插件的新版本时使用已关联平台草稿的项目目录。正式上线前在声明支持的豆包 PC 环境验证安装、版本、帮助、登录、登出和一次无副作用业务调用。

提审要求见 [开放平台操作指南](https://bytedance.larkoffice.com/docx/Y4oadNJ8VoFrWgx3gxcc9qelnTh)和 [Plugin 交付规范](https://bytedance.larkoffice.com/docx/J5o2dZK8hoJItxxNQyocHgRzncb#Tz4jdNIz7oTRMexWxDHcKmAnnbe)。CLI 配置见 [接入指南第 4 章](https://bytedance.larkoffice.com/docx/J5o2dZK8hoJItxxNQyocHgRzncb#doxcnTD7jwohWpGTCdHfF8ZAPQf)。

## CLI 人工接入

按[完整接入指南](https://bytedance.larkoffice.com/docx/J5o2dZK8hoJItxxNQyocHgRzncb)第 4.5 节的 CLI 专项人工接入流程，交付问卷字段、六个平台 ZIP 和配套 Skills。问卷与命令配置维护在 [manual.md](manual.md)。

平台 ZIP 根目录只有一个执行文件：Linux/macOS 为 tiana，Windows 为 tiana.exe；文件名与接入配置入口一致。配套 Skills ZIP 包含五个顶层技能，用户密钥管理位于 tiana-function 内。每个顶层技能目录包含 SKILL.md、资料和 512×512 图标。技能之间按名称衔接任务及结果，文件链接只引用当前技能目录内的资料。

### 构建

在仓库中直接执行，无需传参数（构建机器需有 Python 3、npm 和 Go，且可下载 CLI 及其 Go 模块依赖）：

```sh
./scripts/doubao_packaging
```

脚本查询 CLI、Skills 当前正式版本，通过 Go module 下载对应版本 CLI 源码，编译六个平台二进制并写入默认注册来源；Skills 来自校验过 SHA512 和版本的 agent-skills npm 包。打包输入是解析后的固定版本号；输出目录为 `dist/doubao/cli-<CLI版本>-skills-<Skills版本>/`。

技能使用指定 npm 正式版的完整业务内容，仅增加豆包要求的展示元数据和图标。固定的是交付版本，技能内的安装、登录与更新指令保持原样。

最终交付文件为 `dist/doubao/tiana-doubao-manual-skills-<Skills版本>-cli-<CLI版本>.zip`，旁边附 `.sha256` 文件。沿用原交付的同名顶层目录，脚本最后一行输出整包的绝对路径。

整包内包含六个平台 ZIP、一个五技能 ZIP、`CLI-接入配置与技术手册.md`、`packages.json`、`source-integrities.json`、`cli-source.json`、`README.md`、`TEST-RESULTS.md` 和 `SHA256SUMS`。测试结果文件只记录脚本实际完成的静态打包检查；客户端运行与授权需另行验收。

## Windows ARM64 发布验证

GitHub Actions 的 `Doubao Windows ARM64` 工作流从正式 CLI、Skills 版本构建 v1 六平台交付包，并从当前检出生成 v2 Plugin。在 `windows-11-arm` 上解压同一交付物，以原生 ARM64 Node.js 执行检查：v1 的 ARM64 EXE、v2 配置中的 `npm.cmd` 全新安装及 `tiana.cmd` 入口、版本、帮助、渠道来源、等待授权、本地状态与登出。

工作流保存 `doubao-delivery` 交付附件及 `windows-arm64-results` 日志。认证使用本机模拟服务和独立配置目录；这项检查不包含豆包桌面客户端导入、浏览器交互或生产账号授权，宿主接入仍需单独验收。

### 授权验证

宿主运行 tiana login，等待兑换和保存成功退出后，单独执行 tiana status --auth-only --json；退出码为 0 且 logged_in 为 true 才确认登录。原始正则及 Windows 带 .exe 的命令见手册。

```sh
TIANA_TEST_CLI_BINARY=/absolute/path/to/tiana npm run test:doubao-auth
TIANA_TEST_CLI_BINARY=/absolute/path/to/tiana npm run test:connector-auth
npm run validate:ci
```

认证 fixture 使用真实 CLI 子进程、隔离存储和回环模拟服务；不等同于豆包或 WorkBuddy 桌面验收。每次交付保留平台运行、权限、源二进制一致性及目标客户端待联调项。

CLI 源码只提供通用构建字段；具体渠道值仅由本平台打包脚本指定。平台包升级继续从目标 CLI 版本源码执行该脚本，替换同渠道二进制。宿主仍执行普通 `tiana login`。`version --json` 返回的构建默认来源用于升级前后核验。
