# Windows 安装与 Git helper 排查

在 Agent 实际执行 Git 的环境中检查命令与 PATH。下方示例适用于已有的 PowerShell 工具；不要求从 Bash 嵌套启动 PowerShell。其他终端中的安装结果不能证明 Agent 使用相同的 Node、npm 或 PATH。若任务运行在 WSL 或远程环境，应在那个环境中按[开始使用](getting-started.md)安装。

## 核验安装与入口

需要安装 CLI 时先读 [Windows CLI 安装](windows-install.md)，按实际失败阶段恢复。确认 Node.js 20+、Git for Windows 与安装命令成功后执行：

```powershell
npm.cmd ls --global @tianacloud/cli --depth=0
$npmPrefix = (npm.cmd prefix --global).Trim()
Get-Item (Join-Path $npmPrefix 'git-remote-tiana'), (Join-Path $npmPrefix 'git-remote-tiana.cmd')
where.exe node
where.exe git
where.exe tiana
where.exe git-remote-tiana
tiana.cmd version
tiana.cmd git remote-helper --help
```

`@tianacloud/cli` 同时注册两个命令：`tiana` 和 `git-remote-tiana`。npm 在 Windows 的全局 prefix 目录生成无扩展名的 shell 入口、`.cmd` 与 `.ps1` 入口，后续调用包内的 Node 脚本。`bin/git-remote-tiana.mjs` 存在只证明包内有源文件，还需核验 npm 生成的命令入口和 PATH。

## 按检查结果恢复

| 结果 | 处理 |
| --- | --- |
| `npm ls` 缺包、版本不符，或 prefix 下缺少 helper 入口 | 查看安装错误；`npm.cmd config get bin-links` 应为 `true`。解决安装原因后重装；若明确关闭了命令链接，可在安装命令上加 `--bin-links=true`。由 npm 生成命令入口。 |
| prefix 下入口存在，但 `where.exe` 找不到命令 | 将实际 `$npmPrefix` 加入 Agent 启动环境的 PATH，重新启动 Agent，再在其执行环境中核验。Windows 全局命令目录就是 prefix 本身。 |
| `where.exe` 返回多个位置，或 `tiana` 版本与 `npm ls` 不符 | 核对 Agent 所用 Node/npm 和 PATH 顺序，确保调用本次核验安装的命令。 |
| 命令已找到，但报告原生二进制缺失或下载失败 | 按 [Windows CLI 安装](windows-install.md)区分下载、校验、脚本跳过和解压失败，再处理对应原因。 |

要验证是否只是当前进程缺少 PATH，可在**同一次 PowerShell 调用**中临时加入目录并重试原 Git 操作：

```powershell
$npmPrefix = (npm.cmd prefix --global).Trim()
$env:Path = "$npmPrefix;$env:Path"
where.exe git-remote-tiana
```

这个修改只作用于当前进程及其子进程；Agent 的下一次工具调用可能启动另一个 Shell。持久修复由外围启动环境完成。

Git 处理 `tiana://` 地址时自动调用 helper，由它执行 `tiana git remote-helper`。`--version` 不是 helper 的独立用户命令；CLI 版本用 `tiana.cmd version` 检查。入口恢复后，再按[应用源码与版本发布](../../tiana-git/references/source-releases.md)进行已授权的 Git 操作。认证错误与命令找不到是不同阶段，前者按[开始使用](getting-started.md)恢复登录。

依据：[npm 全局目录规则](https://docs.npmjs.com/cli/v11/configuring-npm/folders/)、[npm Windows 命令入口实现](https://github.com/npm/cmd-shim/blob/main/lib/index.js)、[Git remote helper 协议](https://git-scm.com/docs/gitremote-helpers)。
