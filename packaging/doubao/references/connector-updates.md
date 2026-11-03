# 豆包分平台包与固定版本

本发行版固定 CLI {{CLI_VERSION}}、Skills {{SKILLS_VERSION}}。CLI 的安装位置以豆包实际返回的位置为准。

macOS/Linux 使用 `command -v tiana`；Windows PowerShell 使用 `Get-Command tiana.exe -All` 定位实际文件。豆包返回完整路径时优先使用该路径，并执行版本命令验证。

CLI 路径存在但命令不可见时，将该文件所在目录加入当前 Agent 命令环境的 PATH。路径指向其他版本时使用豆包实际安装的完整路径。

从当前加载的 SKILL.md 路径核对技能根目录，{{SKILL_COUNT}} 份 metadata.version 都应为 {{SKILLS_VERSION}}。更新经新的豆包平台包与配套技能文件交付，重载后核实生效。登录与环境选择见 [开始使用](getting-started.md)。
