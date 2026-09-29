---
name: tiana-ledger
description: 使用 Tiana 创建个人账单与收支记账应用，包含快速记账、月份筛选和分类统计。用户要求账单 app、日常记账或收支管理时使用。
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.2.0"
  parent: tiana
  source: https://github.com/tianacloud/agent-skills/tree/main/skills/tiana-ledger
---

# 拾账 · 账单

使用[完整应用模板](assets/app/src/main.js)、[样式](assets/app/src/style.css)、[自定义下拉](assets/app/src/dropdown.js)和 [SQLite 表结构](assets/app/schema.sql)交付应用。保留清透蓝色账本、月度收支与分类统计与手机布局。首次打开提供快速分类入口，填一个金额即可记账；收入、支出、结余和图表从零开始。

## 创建与发布

按 `tiana-sqlite/references/js-sdk.md` 的“核验目标托管环境”判断就绪状态：复用当前目标环境的有效验证结果；未核验不等于未部署，Bootstrap 接口存在也不等于 SQL 已连通。

1. 加载已安装的 `tiana` 和 `tiana-sqlite`，按应用流程完成账号与数据库检查。CLI 和原生 Git 继承 launcher 的 `TIANA_API_ORIGIN`，技能不设置部署地址。
2. 将 `assets/app/` 复制为独立应用源码，将 [gitignore.template](assets/app/gitignore.template) 重命名为 `.gitignore`。把已核实的 App ID（新建时来自 `tiana web create NAME --json` 的 `data.id`）和数据库实例 ID 分别填入 `public/tiana.app.json` 的 `web_id` 与 `database_instance_id`。模板用该 App ID 区分同库中的应用记录。对选定实例执行 `schema.sql`，首屏保持零记录与可操作的起步引导。
3. 依照 `tiana-sqlite` 的 `references/js-sdk.md` 核验 SDK 与运行时。模板固定的 `@tianacloud/serverless@0.1.0-beta.1` 已核验含 `auth: TianaAuthProvider`；使用 `window.tiana.auth` 与共享 adapter，`connection()` 只供连接元信息。运行 `npm ci`。正式记录通过参数化 SQL 保存到 Tiana SQLite。
4. 按 `tiana/references/source-releases.md` 创建或复用 Tiana Git，保存实际实例 ID 到 `source.json`。提交应用源码、锁文件、SQL、清单与构建配置，再按同一发布指引的“构建时传入源码提交”步骤，在命令工具中核验干净工作树并读取 HEAD，执行 `node scripts/build.mjs <完整提交号>`；[构建脚本](assets/app/scripts/build.mjs)接收该提交号，只向 `dist/tiana.app.json` 写入 Git ID 和完整提交 hash。核对模块、CSS、清单和源码关联字段。
5. 验证远端发布引用指向该源码提交，再发布对应不可变版本。新建应用将 Tiana Git 托管作为交付内容；已有外部仓库按共享流程确认托管范围。
6. 在托管地址新增收支、编辑金额和日期、切换月份及收入/支出筛选、删除一条账单；刷新后核对分币金额和统计一致。检查手机布局、自定义下拉的鼠标/键盘选择和哈希导航。交付应用链接、数据库实例、Tiana Git 仓库、发布引用与源码提交。

加载失败显示可重试的读取入口；写入结果不明先按记录 ID 独立读取核实，不自动重放。进一步调整内容、查询或交互时，阅读[产品与数据说明](references/product.md)。
