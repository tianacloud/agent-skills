# Git helper 准备与 PATH 排查

本豆包发行版提供原生 CLI {{CLI_VERSION}}。Git 的 `tiana://` 远程地址还需要名为 `git-remote-tiana` 的启动入口，该入口调用同一个 CLI 的 `git remote-helper` 子命令。

先核验 `git --version`、`tiana version` 与 `tiana git remote-helper --help`。确认实际执行的 CLI 为 {{CLI_VERSION}}，其目录在当前命令环境 PATH 中。仅在使用原生 Git 且入口缺失时，在当前用户工具目录创建下面的脚本；已有入口时先核实其目标。

## macOS / Linux

```sh
TIANA_HELPER_DIR="$HOME/.tiana/doubao-tools/{{CLI_VERSION}}"
mkdir -p "$TIANA_HELPER_DIR"
printf '%s\n' '#!/bin/sh' 'exec tiana git remote-helper "$@"' > "$TIANA_HELPER_DIR/git-remote-tiana"
chmod 755 "$TIANA_HELPER_DIR/git-remote-tiana"
export PATH="$TIANA_HELPER_DIR:$PATH"
command -v tiana
command -v git-remote-tiana
```

## Windows PowerShell

使用已安装的 Git for Windows。它可以执行下面的无扩展名 shell helper；内容使用 UTF-8 无 BOM、LF 换行。

```powershell
$tianaHelperDir = Join-Path $env:USERPROFILE '.tiana/doubao-tools/{{CLI_VERSION}}'
New-Item -ItemType Directory -Force -Path $tianaHelperDir | Out-Null
$tianaHelperText = '#!/bin/sh' + "`n" + 'exec tiana git remote-helper "$@"' + "`n"
[IO.File]::WriteAllText((Join-Path $tianaHelperDir 'git-remote-tiana'), $tianaHelperText, (New-Object Text.UTF8Encoding($false)))
$env:Path = "$tianaHelperDir;$env:Path"
Get-Command tiana.exe
git --version
```

只在当前任务的 Git 调用环境中传递 helper 目录和豆包 CLI 目录的 PATH；新工具调用不一定继承上一次的环境，需显式携带。让 Git 子进程继承同一 `TIANA_API_ORIGIN`。不要求修改全局 Git 配置或用户启动文件。

核验 helper 能力时，用 `capabilities` 后接空行作为标准输入调用该 helper，预期输出 `connect` 后接空行、退出 0；这只证明入口与协议协商正常，不代表远程读写成功。随后按 [源码流程](../../tiana-git/references/source-releases.md)进行用户授权的 Git 操作。
