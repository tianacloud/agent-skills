# TianaCloud CLI 人工接入配置与技术手册

固定发行：CLI **{{CLI_VERSION}}** / Skills **{{SKILLS_VERSION}}**。整理日期：2026-11-03。
依据：[豆包接入指南第 4.2 节](https://bytedance.larkoffice.com/docx/J5o2dZK8hoJItxxNQyocHgRzncb#TyK6dUDnaouQxbx4h34c9Tm6nFb)，读取的文档 revision 为 1369。

## 接入方式

按当前已在对接的 CLI 专项流程，提交下列问卷字段、五个平台 ZIP 和配套 Skills，由豆包生态团队人工配置与联调。当前指南的 CLI 部分提供问卷字段与人工配置示例，没有定义可由合作方直接导入的分包 cli_config JSON Schema。本文件为字段填写单及技术手册，平台内部配置由生态团队按实际后台规则生成。

## 问卷字段填写单

| 字段 | 本次填写内容 |
| --- | --- |
| 产品展示名 | TianaCloud |
| 产品简介 | 让 AI 创建、修改和部署 Web 应用，管理云端 SQLite、Git 源码及 Go 后端服务。 |
| CLI 安装方式 | 包安装（分平台上传） |
| CLI Runtime 及最低版本 | 不需要外部 Runtime。原生 Go 可执行文件，启动不依赖 Node.js/npm。Web 工程构建仍按项目准备运行时；原生 Git 功能需要系统 Git。 |
| CLI 版本 | {{CLI_VERSION}} |
| 配套 Skills 版本 | {{SKILLS_VERSION}}，共 {{SKILL_COUNT}} 个技能，含 tiana-function 与 tiana-secrets |
| CLI 可执行文件名 | Linux/macOS：tiana；Windows：tiana.exe。实际文件名与平台槽位的入口一致。 |
| CLI 安装命令 | 不适用，使用下面的分平台 ZIP。 |
| CLI 安装包支持平台 | Linux AMD64、Linux ARM64、macOS AMD64、macOS ARM64、Windows AMD64；验收范围见末节。 |
| CLI 是否需要登录 | 需要 |
| CLI 版本升级方式 | 发布新的固定正式版本后重新提供对应平台 ZIP 与 Skills。停止运行旧进程后，在原 CLI 安装位置替换同名二进制；用户级账号状态由 CLI 管理，安装文件与账号文件分别保存。接入团队更新包及技能后核验实际版本。覆盖更新与跨版本会话延续须随版本联调验证；不声明未验证的兼容性或自动更新能力。 |
| CLI 手册 / 命令参考 | 本文件与配套 Skills；CLI 实际命令以 tiana help 和各子命令 --help 为准。 |

## 命令配置

下表中的 Windows 命令保留 .exe 后缀。若平台以完整安装路径执行，请使用平台实际解析到的路径，带空格的路径按所用 Shell 正确引用。

| 能力 | Linux / macOS | Windows |
| --- | --- | --- |
| 版本检查 | `tiana version` | `tiana.exe version` |
| 登录 | `tiana login` | `tiana.exe login` |
| 登录状态检查 | `tiana status --auth-only --json` | `tiana.exe status --auth-only --json` |
| 登出 | `tiana logout` | `tiana.exe logout` |
| 帮助 | `tiana help` | `tiana.exe help` |

登录状态匹配正则（原始正则文本）：

```regex
"logged_in"\s*:\s*true\b
```

若后台以 JSON 字符串保存，等价转义形式为：

```json
"\"logged_in\"\\s*:\\s*true\\b"
```

判定时同时检查命令退出码为 0。

## 分平台 ZIP

| 平台槽位 | 文件 | 根目录唯一入口 | 执行权限 |
| --- | --- | --- | --- |
| linux-amd64 | tiana_linux_amd64.zip | tiana | 0755 |
| linux-arm64 | tiana_linux_arm64.zip | tiana | 0755 |
| darwin-amd64 | tiana_darwin_amd64.zip | tiana | 0755 |
| darwin-arm64 | tiana_darwin_arm64.zip | tiana | 0755 |
| windows-amd64 | tiana_windows_amd64.zip | tiana.exe | Windows 原生 EXE |

文件大小、MD5 和 SHA256 见 `packages.json`。这些字段仅描述实际附件，不含占位资源地址或伪造资源 ID。上传及托管信息由接入团队的平台流程生成。

## 安装与版本核验

把目标平台 ZIP 解压到宿主安装目录，保持根目录文件名不变；Linux/macOS 保留 0755。用实际安装文件执行 version，预期 `tiana {{CLI_VERSION}} (helper-contract 3)`；随后执行 help、login --help 及本次任务所需产品命令的 --help。

{{SKILL_COUNT}} 个 Skills 位于配套 ZIP 的{{SKILL_COUNT}} 个顶层目录，各目录内含 SKILL.md、引用资料和图标。交接给人工接入团队加载；按实际加载目录核对{{SKILL_COUNT}} 份 metadata.version 均为 {{SKILLS_VERSION}}。

## 登录、状态与登出

1. 宿主在非交互式 Shell 中启动单条 `tiana login`；CLI 无需 stdin、TTY 或按回车确认。
2. CLI 创建认证事务、输出完整授权 URL 并尝试启动系统默认浏览器。用户在浏览器中完成账号登录及授权；自动打开失败时仍等待同一事务，可手动打开输出的 URL。
3. CLI 按认证服务返回的间隔查询当前事务，等待批准、拒绝、到期或进程取消；只有兑换及保存用户凭据成功后才退出 0。已打开网页、已输出链接或正在等待均不等于成功。
4. 宿主独立执行本地状态检查；退出 0 且正则命中才确认授权并续接原对话。
5. 失败、取消或过期返回非 0，不续接受保护操作。事务有效期及轮询间隔由认证服务返回，不能由宿主把等待中间状态当成功。宿主终止进程即中止本次等待；本机状态与服务端短期事务是否需要额外清理，应在取消/超时联调中核验。
6. 登出使用 `tiana logout`，未登录时重复执行也应成功；真实已登录的登出可能访问服务端撤销接口，网络失败按实际非 0 错误处理。

`--no-open` 只关闭自动打开浏览器；`--json` 使阻塞登录的 URL/进度输出到 stderr，stdout 只输出最终 JSON。默认接入使用上表中的 `tiana login`。`--start` / `--resume` 是手动 CLI 的分步参数，宿主 Auth 不使用它们。

状态命令的 JSON 中 `data.logged_in` 是布尔值。已登录返回 true；凭据缺失或 access 已过期返回 false，这两种正常检查结果均退出 0。文件读取失败、损坏等执行错误退出非 0。该检查只读取当前管理入口对应的本地凭据及到期时间，不联网、不刷新、不写入；它不证明服务端尚未撤销该凭据，业务请求仍由服务端验证权限。

凭据保存在用户级配置目录的 tiana/credentials.json，按管理入口隔离。Windows 使用当前进程正常读写权限，新文件继承目录权限；CLI 保留文件锁与原子写入。技能与接入材料不包含实际 Token，不需要操作者读取凭据文件。正常帮助和版本命令退出 0；参数或运行错误用非 0 表示。

## 远程依赖与网络要求

- 生产管理入口：`https://console.tianacloud.com`（HTTPS，默认 443）。CLI 通过其管理 API 创建/查询资源及认证事务。
- 认证 API：`/api/v1/auth/transactions`、当前事务的 poll 路径、`/api/v1/auth/token` 及登出撤销接口。浏览器使用事务返回的完整授权 URL；第三方登录跳转域名需按实际生产登录链路记录补齐。
- SQLite、Git、Web、Function 业务地址取资源的实际 Endpoint/回执；模板、素材与文件下载地址取服务端返回的地址，可能包含对象存储域名。部署和防火墙域名清单须结合实际生产资源联调补齐，不把管理域名当作所有数据面地址。
- CLI 使用系统公有 CA 信任。需要经过代理的环境按 CLI 代理说明与实际网络验证；本次已完成的本地检查不代表生产网络或防火墙已验收。
- 此分平台安装模式由豆包分发原生 ZIP，本地 CLI 启动不访问 npm 下载平台包；应用构建依赖由项目自身决定。

## 原生 Git 入口

CLI 包只有一个原生执行文件。`git remote-helper` 能力在同一个 tiana 内；原生 Git 的 tiana:// 地址需要额外的 git-remote-tiana 入口，配套 Skill 在使用 Git 时指导于用户工具目录建立该入口，转调同一个 tiana。Linux 与 Windows 临时 Git 环境已验证入口协商，生产 Git clone/fetch/push 仍需在豆包实际环境验收。

## 权限说明

按照当前用户及所选租户的权限，执行实例管理、数据库查询与修改、Git 源码同步、Web/Function 部署以及文件上传下载，用于完成用户提出的应用开发任务。实际访问范围由服务端账号与资源权限限定；权限说明不能替代平台上需要填写的隐私政策等信息。

## 验收范围

本次包的结构、源包一致性、原生运行与授权回归结果见 TEST-RESULTS.md。平台包和技能内容验证不代表已经完成豆包客户端人工配置与真实授权验收；生产网络域名和各平台业务闭环仍由接入团队联调核验。
