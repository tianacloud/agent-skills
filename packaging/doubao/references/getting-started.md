# 开始使用

本次豆包初始交付 CLI {{CLI_VERSION}}、Skills {{SKILLS_VERSION}}，包含 {{SKILL_COUNT}} 个技能。CLI 由豆包按平台下载原生 ZIP 并安装，Skills 由接入团队加载本次配套技能文件。

## 安装

在 Agent 实际执行命令的环境使用豆包返回的 CLI 安装路径。macOS/Linux 的运行文件为 `tiana`，Windows 为 `tiana.exe`；本说明的 `tiana` 命令均指该原生文件。平台未将安装目录加入 PATH 时，使用实际完整路径，或在当前命令环境加入该目录。

执行 `tiana version`，按入口 SKILL.md 完成本会话的版本检查与更新，再核验任务所需命令的帮助。CLI 原生文件启动不需要 Node.js 或 npm；Web 项目构建仍按项目自身依赖准备运行时。原生 Git 操作需要系统 Git；首次使用时按 [Git helper 准备](windows-git-helper.md)建立入口。

CLI 最低版本为 1.0.4。缺少 CLI 或版本过低时，使用 Node.js 20+ 执行 `npm install -g @tianacloud/cli@latest --include=optional --registry=https://registry.npmjs.org/`，Windows 使用 `npm.cmd`。npm 安装或更新后使用实际生成的 tiana 入口，Windows 使用 tiana.cmd；核验新入口的版本，并在后续调用中沿用其路径。安装环境与 Skills 加载目录按[宿主说明](connector-updates.md)核实，完成后继续用户原任务。

## 更新

{{UPDATE_GUIDE}}

## 授权范围

登录后，CLI 使用当前用户与所选租户的权限管理实例、查询或修改数据库、同步 Git 源码、部署 Web 应用及后端服务、上传下载文件；实际访问范围由服务端权限和目标资源决定。按用户任务调用相应能力。凭据由 CLI 保存在当前用户目录，技能无需读取凭据文件。执行 `tiana logout` 清除本地登录态；`tiana status --auth-only --json` 用于无交互检查本地登录态，普通 `tiana status` 同时查询账号用量。

## 环境与地址

CLI 默认使用生产管理入口 `https://console.tianacloud.com`。继承宿主为本次接入配置的环境；用户明确指定其他管理入口时，将相同 `TIANA_API_ORIGIN` 传给每次 CLI 和 Git 子进程，不写入应用源码或用户启动文件。

管理入口、Web 地址与数据库/Git Endpoint 用途不同。资源地址取实际 CLI 回执；浏览器授权地址取本次认证事务的完整 URL。

## 对话中的登录

豆包连接器的授权命令为 `tiana login`。宿主启动该命令后持续等待；CLI 打开系统浏览器并等待同一事务完成，只有凭据保存成功才以退出码 0 结束。浏览器无法自动打开时展示 CLI 输出的完整授权链接，仍保持该进程等待，用户无需回到终端输入确认。

登录命令完成后，由宿主独立执行 `tiana status --auth-only --json`，退出码 0 且输出中 `"logged_in": true` 才确认登录。尚未授权时引导用户完成豆包登录侧边栏中的授权；失败、取消或超时时说明实际结果，等待用户重试。沿用原对话任务，登录成功后继续。

普通业务调用使用已保存的账号会话。登录状态检查仅读取本地凭据及到期时间；配额问题与账号退出应分别处理。详细命令与错误恢复见 [CLI 指引](cloud-cli.md)。
