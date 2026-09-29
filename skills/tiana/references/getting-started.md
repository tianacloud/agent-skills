# 开始使用

在 Agent 实际执行命令的环境中检查 `tiana --version`、`tiana login --help` 和 `tiana web --help`。CLI 必须具备 `login --start/--resume`、`sqlite`、`git` 和 `web`。命令不存在时先按下方安装。

## 安装

Windows 安装前先阅读 [Windows CLI 安装](windows-install.md)，确认实际 Node 平台、安装版本与日志方式。

通过 npm 安装 `@tianacloud/cli`。安装需要 Node.js 20 或更高版本，并能访问 npm registry 和 Gitee 发布附件；使用 Tiana Git 还需要原生 Git（Windows 使用 Git for Windows）。

```sh
npm install -g @tianacloud/cli --registry=https://registry.npmjs.org/
```

Windows PowerShell 使用 `npm.cmd`；`0.2.2-beta.4` 已改为 Node 内解压 ZIP。该包同时安装 `tiana` 和 `git-remote-tiana`，后者将 Git 请求交给 `tiana git remote-helper`。导入 Skill 不等于安装 CLI；已安装符合要求的版本时直接复用。

安装成功后重新检查版本及命令。安装失败或回滚后，先按失败阶段解决实际安装错误，再决定是否重试和核验，不能以包内存在脚本作为安装成功的依据。Windows 环境中找不到命令时，阅读 [Windows 安装与 Git helper 排查](windows-git-helper.md)。

安装成功后直接执行 `tiana status`，根据 CLI 实际返回的状态继续任务或恢复登录。未执行的命令保持“尚未验证”，不从安装包 README 或环境变量预判登录与部署不可用。CLI 报告具体配置或证书错误时，如实提供错误及 CLI 的处理提示。

## 对话中的登录

1. 执行 `tiana login --start --no-open --json`。
2. 向用户展示 `data.verification_uri`，让用户打开并批准登录。`status=pending`、退出码 3 表示等待授权。
3. 用户完成授权后执行 `tiana login --resume --json`。只有 `status=succeeded` 且 `data.logged_in=true` 才继续；仍等待时保留同一链接并遵循 `data.retry_after`，不要连续创建新登录。
4. 链接失效后重新 start。CLI 本地保存账号登录态，不需要 Connector。

普通终端也可执行 `tiana login`，打开它输出的链接并等待完成。`tiana status` 检查服务端账号和用量；用量接口失败不等于已经退出登录。

命令与恢复见 [CLI 命令与恢复](cloud-cli.md)。
