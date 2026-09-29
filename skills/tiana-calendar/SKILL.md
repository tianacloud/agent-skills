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

1. 加载已安装的 `tiana` 和 `tiana-sqlite`，按应用流程完成账号与数据库检查。CLI 和原生 Git 继承 launcher 的 `TIANA_API_ORIGIN`，技能不设置部署地址。
2. 将 `assets/app/` 复制为独立应用源码，将 [gitignore.template](assets/app/gitignore.template) 重命名为 `.gitignore`。把已核实的 App ID（新建时来自 `tiana web create NAME --json` 的 `data.id`）和数据库实例 ID 分别填入 `public/tiana.app.json` 的 `web_id` 与 `database_instance_id`。模板用该 App ID 区分同库中的应用记录。对选定实例执行 `schema.sql`，首屏保持零记录与可操作的起步引导。
3. 依照 `tiana-sqlite` 的 `references/js-sdk.md` 核验 SDK 与运行时。模板固定的 `@tianacloud/serverless@0.1.0-beta.1` 已核验含 `auth: TianaAuthProvider`；使用 `window.tiana.auth` 与共享 adapter，`connection()` 只供连接元信息。运行 `npm ci`。正式记录通过参数化 SQL 保存到 Tiana SQLite。
4. 按 `tiana/references/source-releases.md` 创建或复用 Tiana Git，保存实际实例 ID 到 `source.json`。提交应用源码、锁文件、SQL、清单与构建配置，再运行 `npm run build`；[构建脚本](assets/app/scripts/build.mjs)读取干净 HEAD，只向 `dist/tiana.app.json` 写入 Git ID 和完整提交 hash。核对模块、CSS、清单和源码关联字段。
5. 验证远端发布引用指向该源码提交，再发布对应不可变版本。新建应用将 Tiana Git 托管作为交付内容；已有外部仓库按共享流程确认托管范围。目标 Bootstrap 未提供账号 provider 时报告发布阻塞。
6. 在托管地址跨月选日、新增并编辑单日定时日程、切换日程列表和删除；刷新核对日期、时间和分类，验证结束时间晚于开始时间。检查手机布局、自定义下拉的鼠标/键盘选择和哈希导航。交付应用链接、数据库实例、Tiana Git 仓库、发布引用与源码提交。

加载失败显示可重试的读取入口；写入结果不明先按记录 ID 独立读取核实，不自动重放。进一步调整内容、查询或交互时，阅读[产品与数据说明](references/product.md)。
