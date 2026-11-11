---
name: tiana-function
description: 使用 Tiana 创建和管理 Go 后端服务，读取及保存 Git 源码、编译发布、修改参数与 CORS、开发 WebSocket 实时接口、在函数中访问文件存储；为 Web 应用开发访问 SQLite 的后端服务，或初始化用户密钥库、列出密钥名称与版本、写入和删除密钥时使用。前端页面开发配合 tiana-web。
license: Apache-2.0
metadata:
  author: Tiana Cloud
  version: "1.0.20"
  parent: tiana
  source: https://github.com/tianacloud/agent-skills/tree/main/skills/tiana-function
---

# Tiana Function

本 skill 负责后端服务的创建与管理、源码、运行参数、用户密钥库、Go 接口、数据库与文件存储访问、编译发布。为 Web 开发后端时，接收 `tiana-web` 技能确定的 Git ID、接口需求和数据依赖；完成后返回服务 ID、source_dir、发布回执、接口契约和参数生效结果，由 Web skill 继续前端接入、绑定、发布及分享验收。

安装、账号与环境选择按 `tiana` 技能。共享各 Tiana 技能本会话的实际更新检查记录；尚未检查时先完成该入口的检查，包括从本会话实际加载的 SKILL.md 的 `metadata.version` 取得 `SKILLS_VERSION`，在同一次 shell 调用中赋值并实际执行 `tiana version check --skills-version "$SKILLS_VERSION" --json` 并按结果自动更新 CLI 和整套 Skills、补齐新增技能并核验，在对话中报告结果与重载要求；`should_notify=false` 也执行。两个包各自比较自身 npm 最新版，检查与安装无需 Tiana 登录；暂不登录或不操作云端资源时仍完成此流程。执行前确认 `tiana function --help` 可用；当前最新正式 CLI 仍缺少命令时，报告配套能力尚未可用及两个包的实际版本，等待已验证的配套发布。

## 创建与修改

按 [后端服务命令](references/commands.md)操作。先确认目标后端服务及其源码 Git，再读取源码。只编辑所需文件，保存得到 Git commit 后显式编译发布。保存源码不会自动编译；发布完成也不会中断正在处理请求的旧进程。如需立即结束当前执行，可在 Console 使用“强制休眠”，下一次请求使用新版本。

新后端服务不自动写入示例。为 Web 开发时传入该应用已确定的 `--git-instance-id GIT_ID`，默认复用 Web 仓库；独立创建且未指定 Git 时由平台创建源码仓库。用 `--source-dir /services/orders` 指定仓库内目录，`/` 表示根目录；省略时默认 `/functions/<名称>/`，中文和大小写保留，名称中的空格替换为下划线；手动指定的目录保留空格。创建后读取 `function show` 的 source_dir，不根据名称或 ID 推导；改名不改变目录。目录是 package main 的编译入口，go.mod 可在该目录或仓库内上级目录；首次保存创建缺失目录，构建只编译指定入口。允许多个服务共享同一目录和源码，分别发布。不要把前端文件或其他后端服务的目录当作本后端服务源码覆盖。

命令回执中的 commit 是仓库主分支提交。并发保存冲突后先保留本地编辑，重读并合并实际变化，再用新 commit 保存；不强推主分支。多文件或二进制资源也可按 `tiana-git` 技能用原生 Git 管理。

## 参数与数据库后端

涉及数据库 Token、第三方 API Key 等敏感配置时，必须先按[参数配置与生效](references/commands.md#参数配置与生效)配置，再按 [Go 后端服务开发](references/go-backend.md)读取与使用。参数更新无需重新编译，但要核对保存回执的应用状态和实际请求结果。

数据库 Endpoint 使用明文参数；Token 和第三方密钥先按[用户密钥库](references/secrets.md)写入密钥，再保存为后端服务的密钥引用参数，不写入 Git、前端源码、业务响应或日志。缺少实际凭据时说明待配置项，不使用占位值宣称联调成功。Web 的数据访问方式、资源绑定与模板制作由 Tiana Web 负责。

后端服务需要访问 SQLite 时，必须先完成 [SQLite 访问配置](references/sqlite-backend.md)：从实例取得 Endpoint、用 CLI 创建 Instance Token、写入密钥库并配置参数，再发布函数和验证真实查询。执行前通过 `tiana token create --help` 核对配套 CLI 能力。

调用方身份通过 SDK 从请求上下文读取，业务需要区分用户数据时使用该身份，不能相信请求体中自报的用户 ID。完成接口核验后，将所需调用身份与数据范围一并交给 Web skill 验证。

App 作者专属的初始化和权限管理接口，按 [App 作者与初始权限](references/go-backend.md#app-作者与初始权限)使用 `caller.IsAppOwner()` 校验；作者指本次来源 Web 的创建者，与租户角色分开。前端的 `is_app_owner` 展示由 Tiana Web 负责。

## 文件存储

函数需要上传、读取、列目录、删除文件或返回浏览器文件 URL 时，先阅读[函数文件存储](references/file-storage.md)，按函数所属租户选择根目录或 Web 子目录，再接入示例。存储连接与凭据由平台注入；业务参数只保存业务配置。结合可信调用身份实现业务权限，完成真实文件读写及浏览器授权访问验收。

## WebSocket

开发实时连接时，按 [WebSocket 实时连接](references/go-backend.md#websocket-实时连接)完成 Go 服务、浏览器原生连接、源码保存和发布验证，再交给 Web skill 绑定与托管验收。

## 用户密钥库

初始化密钥库、查询名称与版本、写入或删除密钥时，阅读[密钥管理](references/secrets.md)。按操作回执报告 key、版本和结果；需要供函数使用时，继续配置密钥引用参数并核验生效。

## 结果与恢复

`accepted` 表示已受理，`publish --wait` 成功才表示发布完成。构建失败后读取 `builds` 和 `logs`，修正源码、额度或配置后重试。响应不确定时沿用原 request ID 和 commit 查询或恢复；不要把再次发起构建当作状态查询。删除后端服务会删除其制品，CLI 保留关联 Git。
