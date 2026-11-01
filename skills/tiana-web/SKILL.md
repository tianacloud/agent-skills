---
name: tiana-web
description: 使用 Tiana 创建、修改、预览和发布 Web 应用。用户要求制作账单、笔记、日历或其他 Web app 时使用；根据实时模板目录和需求决定采用模板或直接开发，并按业务选择直接连接 SQLite 或通过后端服务访问数据库。用户要求把已有 Web app 发布为模板、分享可安装应用链接时也使用。
license: Apache-2.0
metadata:
  author: Tiana Cloud
  version: "1.0.11"
  parent: tiana
  source: https://github.com/tianacloud/agent-skills/tree/main/skills/tiana-web
---

# Tiana Web

安装、登录和通用实例管理见 [Tiana](../tiana/SKILL.md)，SQL 与连接见 [Tiana SQLite](../tiana-sqlite/SKILL.md)，后端服务见 [Tiana Function](../tiana-function/SKILL.md)，源码见 [Tiana Git](../tiana-git/SKILL.md)。

## 每个会话一次的更新检查

**本会话首次使用任一 Tiana 技能时，先完成以下步骤，再开始登录、查询模板或操作应用：**

1. 执行 `tiana version`，按[开始使用](../tiana/references/getting-started.md)核验最低版本；缺少 CLI 或版本过低时，先完成安装或经用户确认的升级。
2. CLI 满足最低版本后，**仍须实际执行** `tiana version check --skills-version 1.0.11 --json`；版本号取实际加载的 metadata.version。这一步检查是否有更新版本。
3. 实际发起检查命令后，才在会话中记为已尝试，并保留返回结果或执行错误。仅运行 `tiana version` 只完成第 1 步。

五个技能共享这份实际调用记录；后续轮次、重复加载或切换技能复用记录，失败也不自动重试。上下文压缩或任务交接时保留记录，新会话重新检查。

仅在 `should_notify=true` 时简短提醒并询问是否升级；用户选择稍后或检查不可用时继续原任务。CLI 仍管理检查缓存和共同的 24 小时提醒额度。升级及重载见[开始使用](../tiana/references/getting-started.md#更新)。

## 数据与素材存储

创建、修改应用或制作模板前，按[数据与素材存储](references/storage-and-assets.md)核对现有实现与干净构建。程序随 Web 打包；优化后、编码前不超过 16 KiB 的静态小图片内嵌 JS；其他外置素材与用户文件使用文件存储，持久业务记录使用数据库。含预置素材时读取[模板素材文件](references/template-files.md)，准备本次应用目录或格式 2 安装材料，并核验目标环境能力。

## 将已有应用发布为模板

用户要求“把某个 Web App 发布为模板”或分享可安装链接时，阅读[用户模板分享](references/share-template.md)，在独立副本中整理源码、结构与个人无关 seed，再打包、上传并交付安装链接。默认包含源码，可让用户选择仅安装；必须制作预览和封面，并按[预览的响应式展示与验收](references/share-template.md#预览的响应式展示与验收)完成 PC 和手机适配。无法判断 seed 是否涉及个人信息时，先让用户选择。用户提供分享链接要求做同款时，也按该文档取得源码并开始新工程。此分支直接处理指定应用。

## 开发与普通发布：查询当前模板目录

**每次创建、修改或普通发布 Web 应用，都必须实际执行 `tiana web list-template --json`。同一会话之前查过、记得某个模板、用户未提模板，都不能代替这次调用。** 有 `data.next_cursor` 时，以 `--after CURSOR` 继续查询本次需求需要的目录页。检查命令实际成功；当前目录不可用时说明结果并按通用方式继续，不能从旧列表选包。

用户只需描述应用。根据本次返回的 `name`、`description` 判断核心功能、数据模型与可定制范围：合适的模板可加速制作，局部差异在工程中修改；没有合适模板就直接开发。已有工程继续修改自己的工程。以需求为依据决定，不要求用户选择模板，也不硬编码模板名称或模板版本。

## 选择数据访问方式

简单应用优先直接访问 SQLite。复杂业务、敏感数据或配置、需要限制用户可见数据时，采用后端服务，必须阅读[带后端服务的 Web 开发流程](references/backend-apps.md)。默认复用 Web 的 Git，后端私有数据库不绑定 Web。

本 skill 负责选择访问方式、前端开发、Web 资源绑定、预览、发布与分享验收。后端的创建、源码、参数配置与读取、数据库访问和编译发布由 [Tiana Function](../tiana-function/SKILL.md)负责；取得后端发布结果后回到本流程完成前端接入。

## 展示当前用户

应用需要展示登录用户、昵称或区分用户与应用所属租户时，阅读[当前用户信息](references/csr-apps.md#当前用户信息)，使用同源会话接口取得实际字段。

需要 App 作者专属界面或初始权限管理时，用会话的 `is_app_owner` 判断当前用户是否为该 Web 的创建者，具体见[App 作者判断](references/csr-apps.md#app-作者判断)。后端权限校验交由 Tiana Function 的 `caller.IsAppOwner()`，前端只控制展示。

## 创建、初始化和发布

1. 阅读 [Web 开发与发布](references/csr-apps.md)；前端直连模式再读 [JavaScript 连接](../tiana-sqlite/references/js-sdk.md)。新应用默认为本次需求创建所需的 SQLite 和 Git 实例，并等待就绪、保存实际 ID；仅在用户明确指定已有实例时核实后复用。修改已有工程时沿用其已确认绑定。实例名称按当前应用命名，模板变量使用 CLI 回执中的 ID。先确定最终入口路径；创建 Web 时用 `--entry` 固定入口，按所选访问方式配置数据库或后端服务绑定，并配置 Git 绑定，并等就绪。Web ID 取 `web create` 返回的 `data.id`。
2. 采用模板时，执行 `tiana web init-template NAME --dir PROJECT_DIR --json`。PROJECT_DIR 是用户项目的不存在目录，位于技能安装目录之外。CLI 下载并原样解压；按 [模板初始化](references/template-init.md)读取工程根部 `metadata.json`，由 Agent 完成全部变量替换及 SQLite 数据初始化。
3. 直接开发时，使用 [固定 index.html](references/index.html)、哈希路由、支持动态账号鉴权的 SDK，按实际数据库结构编写应用及构建清单。
4. **模板和直接开发都由 Agent 处理数据库初始化。** 模板先执行已配置且存在的 schema，再执行已配置且存在的 seeds；两项独立跳过，SQL 失败先核对结果并停止后续发布。普通源码开发还须按[模板素材文件](references/template-files.md)准备新 Web ID 的预置素材；`web publish` 只发布程序包。
5. 构建前按[应用图标](references/csr-apps.md#应用图标)准备真实 PNG：使用用户指定图片或已有的合适图标；需要制作时优先调用可用的 AI 生图工具，以应用核心功能设计图形图标。图片保存到源码，查看缩小后的效果，并核验干净构建根目录和发布包中都有该图片。
6. 按用户需求完成交互和定制。采用后端服务时，先完成[后端交接与接入验证](references/backend-apps.md)，再交付可用前端。安装依赖并从确定源码提交构建；按 [源码版本流程](../tiana-git/references/source-releases.md)完成源码同步，用 `web publish` 发布当前归档，再用 `web status --publish-id` 核对。除非用户仅要求本地开发，交付实际托管地址、资源 ID 和对应源码提交；未验证的阶段如实说明。

## 素材、文件上传、预览与下载

应用有外置素材或用户文件时，阅读[WebApp 文件存储](references/files.md)，核对配套目标环境后使用平台提供的 `context.files`。先创建 WebApp 获得 ID 即可本地预览，无需先发布；文件路径相对于该 WebApp 的目录。没有上传 UI 的应用也须核对预置素材，不能依赖作者的文件链接。
