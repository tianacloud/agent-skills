# Windows CLI 安装

先在 Agent 实际执行命令的环境中检查现有 `tiana --version`、`tiana login --help`、`tiana web --help`；PowerShell 使用 `tiana.cmd`。符合[开始使用](getting-started.md)要求就直接复用，不因此前采用过手工安装而重新安装。导入 Skill 不会安装 CLI。

## 确认环境，再安装一次

运行 `node -p "process.platform + ' ' + process.arch"` 确认实际 Node 平台。Windows Node 返回 `win32`，即使外层是 Git Bash，也走 Windows 安装器；WSL/Linux Node 则按[开始使用](getting-started.md)安装 Linux CLI。其他终端安装成功不能证明 Agent 使用同一套 Node、npm、全局 prefix 和 PATH。

已发布的 `@tianacloud/cli@0.2.2-beta.4` 在 Node 进程内解压 ZIP。安装链路为 npm → Node `postinstall` → 下载 Gitee 发布附件 → 校验 SHA-256 → 提取 `tiana.exe` → 放置原生二进制，解压不依赖 PowerShell。

在允许该安装链路的 Windows PowerShell 环境中，使用 Node.js 20+，执行：

```powershell
npm.cmd install --global @tianacloud/cli@latest --registry=https://registry.npmjs.org/ --foreground-scripts
$installExit = $LASTEXITCODE
```

`--foreground-scripts` 让 npm 显示安装脚本输出，不改变子进程权限。已有可用命令工具时直接使用；不要为了安装从 Bash 再嵌套启动 PowerShell。已明确收到沙箱禁止子进程的结果时，直接按下表处理，不重复尝试同一链路。

若已知工具不回传 stdout/stderr，在第一次执行时将输出写入可读取的日志，并在**同一次工具调用**中立即保存退出码，再用文件读取工具查看两者：

```powershell
$installLog = Join-Path $env:TEMP 'tiana-cli-install.log'
$installResult = Join-Path $env:TEMP 'tiana-cli-install.exit.txt'
npm.cmd install --global @tianacloud/cli@latest --registry=https://registry.npmjs.org/ --foreground-scripts *> $installLog
$installExit = $LASTEXITCODE
Set-Content -Path $installResult -Value $installExit
```

这是上一安装命令的日志写法，二选一；不要仅为捕获输出重装。无输出不代表成功；有现成日志时先读取。

## 按失败阶段处理

| 证据 | 下一步 |
| --- | --- |
| 下载失败、连接超时或 HTTP 错误 | 根据日志修复对应 npm registry 或 Gitee 附件访问，再重试安装。 |
| SHA-256 不匹配 | 保留校验失败信息，核对官方发布附件；不跳过校验，不安装该附件。 |
| Node 启动子进程返回 `EBUSY` 等错误，但没有明确的策略拒绝 | 保留原始错误、失败阶段与实际 Node/可执行文件路径；不凭错误码认定是沙箱或本机策略，不因换 Shell 就假定已修复。没有新的环境证据时不重复安装；将安装器启动失败交由安装环境排查。 |
| 日志显示解压阶段启动 `powershell.exe` 失败 | 这是旧版安装器路径。使用上方命令安装 `@latest`（已发布修复版为 `0.2.2-beta.4`），核对日志中的实际版本；无需更换外层 Shell 或补装 PowerShell。 |
| 当前官方安装命令被明确的执行策略拒绝 | 记录被拒绝的命令与执行层级，由获准的安装环境完成后再回到 Agent 核验。 |
| 安装脚本被跳过，包与命令入口存在但原生二进制缺失 | `--ignore-scripts` 不会完成 CLI 安装。仅在确认脚本执行获准且先前只是误跳过时，执行 `npm.cmd rebuild --global @tianacloud/cli --ignore-scripts=false --foreground-scripts`，然后核验；它仍会调用相同安装器，不能解决沙箱拒绝。 |
| 安装退出码为 0，但命令找不到或版本不一致 | 按 [Windows Git helper 与 PATH 排查](windows-git-helper.md)检查实际 prefix、入口与 PATH，不先重装。 |

不把 `--ignore-scripts` 加自行下载、校验和摆放二进制作为默认替代安装流程。附件或 exe 的哈希匹配只能证明与对应期望值一致，不能单独证明手工安装与官方流程等价；官方安装器当前使用包内 `release.json` 的附件 SHA-256，不把其他清单的二次校验描述为官方安装步骤。失败后先读错误；当前安装器会清理自身临时解压目录，无需先卸载 CLI 或清空 npm 缓存。

成功后在 Agent 的实际环境中核验 `tiana.cmd --version`、`tiana.cmd login --help`、`tiana.cmd web --help`。需要 Tiana Git 时再按 [Git helper 排查](windows-git-helper.md)核验 Git for Windows 和 helper。安装阻塞时说明具体失败阶段，仍可继续不依赖 CLI 的本地工作。登录、资源创建和发布尚未执行就标为未执行，不将它们列为已确认的额外故障，也不宣称安装或发布成功。

依据：[CLI 安装器源码](https://github.com/tianacloud/cli/blob/main/packaging/npm/bin/install.mjs)、[npm foreground-scripts](https://docs.npmjs.com/cli/v11/using-npm/config/#foreground-scripts)、[npm rebuild](https://docs.npmjs.com/cli/v11/commands/npm-rebuild/)、[PowerShell 输出重定向](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_redirection)。
