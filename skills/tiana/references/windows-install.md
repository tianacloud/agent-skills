# Windows CLI 安装

在 Agent 实际执行命令的环境核验 `node -p "process.platform + ' ' + process.arch"`、`tiana.cmd version` 及所需帮助。Windows Node 返回 win32，Git Bash 外层不改变它；WSL 的 Linux Node 选择 Linux 包。

使用 Node.js 20+ 和 npm，从 registry 安装主包及当前平台包：

```powershell
npm.cmd install --global @tianacloud/cli@latest --registry=https://registry.npmjs.org/
$installExit = $LASTEXITCODE
```

npm 通过 os/cpu 选择 cli-win32-x64 或 cli-win32-arm64；二进制直接在平台包的 bin/tiana.exe 中。主包的 tiana/git-remote-tiana 入口定位它后运行。安装不依赖 postinstall 或其他下载源，保留 optional dependencies，使用 --ignore-scripts 同样可行。

已有可用命令工具直接使用，无需嵌套启动别的 Shell。输出不可见时，在同一次调用中保存日志与退出码；没有输出不等于成功。安装失败按 npm 的实际错误处理；缺少平台依赖时检查 optional 配置和实际 Node 平台。权限拒绝交给获准的安装环境，不重复同一失败操作。

成功后核验 `tiana.cmd version`、`tiana.cmd login --help`、`tiana.cmd web list-template --help`、`tiana.cmd web init-template --help`。需要 Git 时安装 Git for Windows，按 [helper 与 PATH 排查](windows-git-helper.md)确认命令位置。npm 安装成功但 PATH 不可见时先检查 prefix 和 Agent 实际环境。

[开始使用](getting-started.md)说明登录、更新检查及用户确认升级。命令尚未执行时如实说明，不把安装阶段的问题当成服务登录或发布故障。
