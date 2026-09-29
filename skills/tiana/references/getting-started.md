# 开始使用

在 Agent 实际执行命令的环境中检查 `tiana --version`、`tiana login --help` 和 `tiana web --help`。CLI 必须具备 `login --start/--resume`、`sqlite`、`git` 和 `web`。命令不存在时先按下方安装。

## 安装

Windows 安装前先阅读 [Windows CLI 安装](windows-install.md)，确认实际 Node 平台、安装器子进程要求与日志方式。

通过 npm 安装 `@tianacloud/cli`。安装需要 Node.js 20 或更高版本，并能访问 npm registry 和 Gitee 发布附件；使用 Tiana Git 还需要原生 Git（Windows 使用 Git for Windows）。

```sh
npm install -g @tianacloud/cli --registry=https://registry.npmjs.org/
```

Windows PowerShell 使用 `npm.cmd`；切换外层 Shell 不会消除安装器内部的 PowerShell 子进程。该包同时安装 `tiana` 和 `git-remote-tiana`，后者将 Git 请求交给 `tiana git remote-helper`。导入 Skill 不等于安装 CLI；已安装符合要求的版本时直接复用。

安装成功后重新检查版本及命令。安装失败或回滚后，先按失败阶段解决实际安装错误，再决定是否重试和核验，不能以包内存在脚本作为安装成功的依据。Windows 环境中找不到命令时，阅读 [Windows 安装与 Git helper 排查](windows-git-helper.md)。

管理端选择由外围环境负责。需要指定部署时，由用户或运行器在启动 Agent 或 Shell 前设置 `TIANA_API_ORIGIN`；技能不执行 export、不按命令注入或覆盖该变量，不修改 Shell 启动文件或技能安装文件。原生 Git 与 CLI 继承同一环境。

直接执行 `tiana status`。CLI 可以复用唯一已保存的管理地址；如果报告地址缺失或多个地址无法选择，说明需在外围启动环境中配置，再重新运行。不要猜测部署地址。私有 CA 使用既有 `TIANA_CA_FILE` 或用户提供的 `--ca-file`；不要关闭 TLS 校验。

## 对话中的登录

1. 执行 `tiana login --start --no-open --json`。
2. 向用户展示 `data.verification_uri`，让用户打开并批准登录。`status=pending`、退出码 3 表示等待授权。
3. 用户完成授权后执行 `tiana login --resume --json`。只有 `status=succeeded` 且 `data.logged_in=true` 才继续；仍等待时保留同一链接并遵循 `data.retry_after`，不要连续创建新登录。
4. 链接失效后重新 start。CLI 本地保存账号登录态，不需要 Connector。

普通终端也可执行 `tiana login`，打开它输出的链接并等待完成。`tiana status` 检查服务端账号和用量；用量接口失败不等于已经退出登录。

命令与恢复见 [CLI 命令与恢复](cloud-cli.md)。
