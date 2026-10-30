---
name: tiana-function
description: 使用 Tiana 创建和管理 Go 后端服务，读取及保存 Git 源码、编译发布、修改参数与 CORS；为 Web 应用开发访问 SQLite 的后端服务时使用。前端页面开发配合 tiana-web。
license: Apache-2.0
metadata:
  author: Tiana Cloud
  version: "1.0.10"
  parent: tiana
  source: https://github.com/tianacloud/agent-skills/tree/main/skills/tiana-function
---

# Tiana Function

安装、账号与环境选择按 [Tiana](../tiana/SKILL.md)。共享各 Tiana 技能本会话的实际更新检查记录；尚未检查时先完成该入口的检查，包括实际执行 `tiana version check --skills-version 1.0.10 --json`。执行前确认 `tiana function --help` 可用；缺少命令时使用配套 CLI，不将未部署能力描述为可用。

## 创建与修改

按 [后端服务命令](references/commands.md)操作。先确认目标后端服务及其源码 Git，再读取源码。只编辑所需文件，保存得到 Git commit 后显式编译发布。保存源码不会自动编译；发布完成也不会中断正在处理请求的旧进程。需要立即采用新版本时用 `function switch`，等待当前请求完成后休眠，下次请求使用新版本。

新后端服务不自动写入示例。未指定 Git 时由平台创建源码仓库；用户要求与 Web 或其他后端服务共仓时传 `--git-instance-id GIT_ID`。用 `--source-dir /services/orders` 指定仓库内目录，`/` 表示根目录；省略时默认 `/functions/<名称>/`，中文和大小写保留，名称中的空格替换为下划线；手动指定的目录保留空格。创建后读取 `function show` 的 source_dir，不根据名称或 ID 推导；改名不改变目录。目录是 package main 的编译入口，go.mod 可在该目录或仓库内上级目录；首次保存创建缺失目录，构建只编译指定入口。允许多个服务共享同一目录和源码，分别发布。不要把前端文件或其他后端服务的目录当作本后端服务源码覆盖。

命令回执中的 commit 是仓库主分支提交。并发保存冲突后先保留本地编辑，重读并合并实际变化，再用新 commit 保存；不强推主分支。多文件或二进制资源也可按 [Tiana Git](../tiana-git/SKILL.md)用原生 Git 管理。

## 参数与数据库后端

参数通过 `function parameters` 管理，由 Go SDK 的 `function.ReadConfig()` 读取，使用 `params.Get("参数名")` 获取值及是否存在。示例和运行约定见 [Go 后端服务开发](references/go-backend.md)。参数与 CORS 保存后无需重新编译。

简单应用可以直接连接 SQLite。业务规则复杂、包含敏感数据或需要按用户限制数据范围时，用后端服务处理业务和数据库操作，前端只调用后端服务。将数据库 Endpoint 与 Token 保存在后端服务参数中，Web 不绑定这个私有数据库；不把数据库 Token 放入前端源码、响应或日志。Web 页面与分享流程配合 [Tiana Web](../tiana-web/SKILL.md)。配置 Web 的后端服务列表后使用 `context.functions.fetch`；复制成模板时读取[后端服务模板](../tiana-web/references/function-templates.md)。

调用方身份通过 SDK 从请求上下文读取，业务需要区分用户数据时使用该身份，不能相信请求体中自报的用户 ID。分享验收应使用另一个账号的 Site 登录，确认业务成功且浏览器无法取得私有数据库连接。

## 结果与恢复

`accepted` 表示已受理，`publish --wait` 成功才表示发布完成。构建失败后读取 `builds` 和 `logs`，修正源码、额度或配置后重试。响应不确定时沿用原 request ID 和 commit 查询或恢复；不要把再次发起构建当作状态查询。删除后端服务会删除其制品，CLI 保留关联 Git。
