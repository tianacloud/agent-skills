---
name: tiana
description: 使用 Tiana Cloud 创建和发布应用、管理实例与 CLI 登录，并将应用版本源码同步到 Tiana Git。通用应用任务从此技能开始；已有对应模板时从模板技能开始并引用本技能；数据库查询与连接使用 tiana-sqlite，数据库分支管理使用 tiana-branches。
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.2.0"
  source: https://github.com/tianacloud/agent-skills/tree/main/skills/tiana
---

# Tiana Cloud

本技能使用 `@tianacloud/cli`，包中同时提供 `tiana` 与 `git-remote-tiana`。安装 CLI 或通过浏览器登录时，阅读[开始使用](references/getting-started.md)；Windows 安装前阅读 [Windows CLI 安装](references/windows-install.md)，命令或 Git helper 找不到时阅读 [PATH 与 helper 排查](references/windows-git-helper.md)。

直接使用 CLI 执行当前任务，根据实际命令结果处理登录或错误。CLI 安装失败时报告安装阶段的问题，后续命令尚未执行的结果保持未知。

## 选择工作流程

收到“安装 skills 并创建应用”的组合请求时，技能安装完成后继续创建应用。用户需求匹配下表的应用模板时，从对应模板开始；其他任务按任务类型选择流程，共享指引按需读取。技能来源仓库仅用于取得技能，模板复制到独立应用项目后再执行应用命令，其 Git remote 不作为客户应用的源码托管选择。

| 任务 | 指引 |
| --- | --- |
| 创建或发布 Tiana 应用 | 按下方应用流程操作。 |
| 创建备孕陪伴、学习管理或协作白板应用 | 分别使用 [备孕](../tiana-two-to-three/SKILL.md)、[学习](../tiana-study/SKILL.md) 或 [白板](../tiana-whiteboard/SKILL.md) 的完整模板，再按本技能发布。 |
| 创建账单、记事本或日历应用 | 分别使用 [账单](../tiana-ledger/SKILL.md)、[记事本](../tiana-notes/SKILL.md) 或 [日历](../tiana-calendar/SKILL.md) 的完整模板，再按本技能发布。 |
| 管理实例或恢复 CLI 凭据 | 按下方实例管理流程操作。 |
| 查询 SQLite、查看表结构或连接应用代码 | 使用 `tiana-sqlite`。 |
| 列出、创建或删除 SQLite 数据库分支 | 使用 [Tiana 分支](../tiana-branches/SKILL.md)。 |

按当前任务读取对应技能和直接链接的参考资料；相对路径以本 `SKILL.md` 所在目录为基准，跨技能路径按已安装技能位置解析。普通应用任务无需读取技能仓库的 `docs/`、`packaging/` 或根目录构建脚本；这些资料服务于技能分发和 Connector 维护。应用模板复制到项目目录后，在该目录安装依赖、构建和执行 Git。明确的 SQL 或分支管理任务可以直接从对应技能开始。

## 创建和发布应用

一并阅读[应用开发与发布](references/csr-apps.md)与 [JavaScript 数据库连接](../tiana-sqlite/references/js-sdk.md)，按其中的接口实现应用。使用平台渲染的固定 [index.html 模板](references/index.html)、哈希路由和 `tiana.app.json`。已提供且已核实的工具、数据库和表结构直接复用；缺少哪项再查询哪项。应用连接实际使用的 Tiana 数据库，必须使用新版 SDK/Bootstrap 的动态账号鉴权，不保留静态 Token 回退。除非用户只要求本地开发，否则完成构建和清单核对后发布，并以 CLI 状态确认版本。六个模板交付托管链接供用户自行检查交互；浏览器验证按用户明确要求或连接故障排查需要开展。确认环境能力缺失时报告实际阻塞，未验证时如实说明。

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
