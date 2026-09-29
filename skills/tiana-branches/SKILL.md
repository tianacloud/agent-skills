---
name: tiana-branches
description: 使用 Tiana CLI 列出、创建和删除 SQLite 数据库分支，设置创建时的来源、历史时间、描述和 TTL，并处理等待与结果不确定的情况。分支内 SQL 查询和连接使用 tiana-sqlite；Git 源码分支使用 tiana 的源码发布流程。
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.2.0"
  parent: tiana
  source: https://github.com/tianacloud/agent-skills/tree/main/skills/tiana-branches
---

# Tiana 数据库分支

通过 `tiana sqlite branch` 管理数据库分支。安装与登录使用 [Tiana](../tiana/SKILL.md)，分支内查询使用 [Tiana SQLite](../tiana-sqlite/SKILL.md)。相对路径以本 `SKILL.md` 所在目录为基准；分开安装时从已安装技能目录表定位同名依赖。

## 按任务阅读

- 列出、创建或删除分支：阅读 [CLI 操作](references/cli.md)。
- 核对实例、分支和 Endpoint 身份，或处理等待中断：阅读 [身份与操作结果](references/lifecycle-model.md)。

## 操作原则

- 先确定完整实例 ID，再核对分支名称和 ID。`--parent`、`--branch` 按精确名称选择；默认分支的固定 ID 是 `main`。
- 创建、删除默认只报告受理；需要等待结果时加 `--wait`。创建成功后再取得该分支连接信息。
- 创建结果未知时先检查原实例下的分支和已报告的操作信息，不直接重跑 create；当前 CLI 没有分支创建的本地恢复机制。
- 删除前确认目标和用户授权；结果未知时保留原实例 ID、分支 ID，核实后仅按原 ID 重试。
- 当前 CLI 只提供分支 `list/create/delete`。重命名、reset、历史列表及修改已有分支保护或过期设置尚无对应 CLI 子命令；遇到这些请求说明 CLI 边界，不编造命令或改用 Control 草案接口。

部署是否支持相应能力，以实际 CLI 返回为准；命令已实现不代表当前服务部署已验证。
