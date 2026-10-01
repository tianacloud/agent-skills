---
name: tiana-calendar
description: 使用 Tiana 创建个人日历应用，包含月历、日程列表和当天安排。用户要求日历 app、个人日程或生活安排应用时使用。
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.2.0"
  parent: tiana
  source: https://github.com/tianacloud/agent-skills/tree/main/skills/tiana-calendar
---

# 朝夕 · 日历

使用[完整应用模板](assets/app/src/main.js)、[样式](assets/app/src/style.css)、[自定义下拉](assets/app/src/dropdown.js)和 [SQLite 表结构](assets/app/schema.sql)交付应用。保留暖橙色月历与当天安排与手机布局。首次打开提供阅读、散步和聚餐建议；点选日期后直接添加第一个日程。

## 创建与发布

相对路径以本 `SKILL.md` 所在目录为基准；跨技能链接指向已安装的 `tiana` / `tiana-sqlite`。客户端将技能分开存放时，按技能目录表定位同名技能，再读取对应文件；依赖未安装时补齐该技能。将 `assets/app/` 复制到技能安装目录及技能仓库检出之外的独立应用项目后，再在应用目录执行 npm、Git 和构建命令。技能来源仓库的 Git remote 不属于该应用。按步骤读取引用资料，无需遍历技能仓库的维护文档或打包目录。

完成构建、清单与源码关联核对后发布到 Tiana，以 CLI 发布状态确认交付。页面交互和实际使用由用户打开托管链接自行检查；本流程不要求 Agent 安装或调用浏览器自动化工具，也不以浏览器验收作为发布前置步骤。

1. 加载已安装的 `tiana` 和 `tiana-sqlite`，按应用流程完成账号与数据库检查。
2. 将 `assets/app/` 复制为独立应用源码，将 [gitignore.template](assets/app/gitignore.template) 重命名为 `.gitignore`。把已核实的 Web ID（新建时来自 `tiana web create NAME --json` 的 `data.id`）和数据库实例 ID 分别填入 `public/tiana.app.json` 的 `web_id` 与 `database_instance_id`。模板用该 Web ID 区分同库中的应用记录。对选定实例执行 `schema.sql`，首屏保持零记录与可操作的起步引导。
3. 依照 [JavaScript 数据库连接](../tiana-sqlite/references/js-sdk.md) 核对 SDK 依赖与运行时接口用法。模板固定的 `@tianacloud/serverless@0.1.0-beta.1` 已核验含 `auth: TianaAuthProvider`；使用 `window.tiana.auth` 与共享 adapter，`connection()` 只供连接元信息。运行 `npm ci`。正式记录通过参数化 SQL 保存到 Tiana SQLite。
4. 按 [源码发布指引](../tiana/references/source-releases.md) 创建或复用 Tiana Git，保存实际实例 ID 到 `source.json`。提交应用源码、锁文件、SQL、清单与构建配置，再按同一发布指引的“构建时传入源码提交”步骤，在命令工具中核验干净工作树并读取 HEAD，执行 `node scripts/build.mjs <完整提交号>`；[构建脚本](assets/app/scripts/build.mjs)接收该提交号，只向 `dist/tiana.app.json` 写入 Git ID 和完整提交 hash。核对模块、CSS、清单和源码关联字段。
5. 验证远端发布引用指向该源码提交，再发布对应不可变版本。新建应用将 Tiana Git 托管作为交付内容；已有外部仓库按共享流程确认托管范围。
6. 发布后用 `tiana web status` 核对版本与源码关联字段，交付应用链接、数据库实例、Tiana Git 仓库、发布引用与源码提交，请用户打开应用自行检查。报告“已发布”，不将发布成功表述为交互已验证。

加载失败显示可重试的读取入口；写入结果不明先按记录 ID 独立读取核实，不自动重放。进一步调整内容、查询或交互时，阅读[产品与数据说明](references/product.md)。
