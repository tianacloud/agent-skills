---
name: tiana
description: 使用 Tiana Cloud 创建和发布应用、管理实例与 CLI 登录，并将应用版本源码同步到 Tiana Git。Tiana 应用任务从此技能开始；数据库查询与连接使用 tiana-sqlite，数据库分支设计使用 tiana-branches。
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.2.0"
  source: https://github.com/tianacloud/agent-skills/tree/main/skills/tiana
---

# Tiana Cloud

本技能使用 `@tianadb/cli` Beta 版本。安装 CLI 或通过浏览器登录时，阅读[开始使用](references/getting-started.md)。

管理端选择由外围运行环境负责。如需指定部署，由用户或运行器在启动 Agent 或 Shell 前设置 `TIANA_API_ORIGIN`。技能直接执行 `tiana` 和原生 Git 命令，继承现有环境；不设置、覆盖或逐命令注入该变量，不维护部署地址配置文件。CLI 报告地址缺失或歧义时，说明需由外围环境配置后重新运行，不自行选择部署。

## 选择工作流程

| 任务 | 指引 |
| --- | --- |
| 创建或发布 Tiana 应用 | 按下方应用流程操作。 |
| 管理实例或恢复 CLI 凭据 | 按下方实例管理流程操作。 |
| 查询 SQLite、查看表结构或连接应用代码 | 使用 `tiana-sqlite`。 |
| 规划数据库分支生命周期或未来的分支客户端 | 使用 `tiana-branches`（仅供设计）。 |

按当前任务读取对应技能和参考资料。明确的 SQL 或分支设计任务可以直接从对应技能开始。

## 创建和发布应用

一并阅读[应用开发与发布](references/csr-apps.md)与 [JavaScript 数据库连接](../tiana-sqlite/references/js-sdk.md)，按其中的接口实现应用。使用固定的 [index.html 模板](references/index.html)、哈希路由和 `tiana.app.json`。已提供且已核实的工具、数据库和表结构直接复用；缺少哪项再查询哪项。应用连接实际使用的 Tiana 数据库，必须使用新版 SDK/Bootstrap 的动态账号鉴权，不保留静态 Token 回退。除非用户只要求本地开发，否则在托管运行时具备该能力后发布并交付访问地址；能力未就绪时报告发布阻塞。

发布托管版本时，按[应用源码与版本发布](references/source-releases.md)确认源码托管授权、关联 Tiana Git，并在发布托管产物前同步该版本对应的源码提交。仅开发本地版本时无需执行源码同步和发布步骤。

## 管理实例

执行管理命令前，阅读 [CLI 命令与恢复](references/cloud-cli.md)。通过 CLI 操作，不直接发送管理 HTTP 请求。

1. 执行 `tiana status` 检查账号与租户用量。需要登录时，按[开始使用](references/getting-started.md)展示浏览器登录链接，等 CLI 确认登录后继续。
2. 用 `tiana sqlite list/show` 或 `tiana git list/show` 定位实例。名称有歧义时让用户选择，后续使用完整实例 ID。
3. 新建资源使用 `tiana sqlite create NAME --wait` 或 `tiana git create NAME --wait`。记录返回的实例和操作标识；成功等待资源就绪后才能连接。表结构和数据操作使用 `tiana-sqlite`。
4. 创建中断且 CLI 保留待完成请求时，使用相同的产品、名称和参数恢复原请求。若上次已成功返回并清理待完成记录，再次 create 会创建新资源；先用 show 核实原实例，不通过重复创建修复连接。

## 凭据与结果

- CLI 保存账号登录态；连接使用有效的账号访问凭据。缺少或过期时登录后复用原实例。
- 不读取凭据文件、输出密钥或手动向命令注入 Token。资源创建不再以 `credential_saved` 为完成条件。
- 资源标识、创建状态与认证边界见[实例与凭据](references/instances-and-tokens.md)。
- 根据命令实际输出判断结果。实例创建的 accepted 只表示受理；使用 `--wait` 或检查实例状态确认就绪。应用发布的 JSON 结果需检查 `status`、`data`、`error` 及实际托管地址。
