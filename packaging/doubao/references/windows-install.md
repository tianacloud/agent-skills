# Windows CLI 安装

在豆包中安装 Windows AMD64 平台包；ZIP 根目录唯一文件为 `tiana.exe`。使用宿主实际返回的路径执行，或把该文件所在目录加入当前 Agent 命令环境的 PATH。

PowerShell 核验：

```powershell
Get-Command tiana.exe -All
tiana.exe version
tiana.exe login --help
tiana.exe web list-template --help
tiana.exe function --help
```

版本应为 {{CLI_VERSION}}。需要 Git 时使用 Git for Windows，按 [Git helper 准备](windows-git-helper.md)建立入口。登录及 Skills {{SKILLS_VERSION}} 的核验见 [开始使用](getting-started.md)。
