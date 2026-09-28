---
name: tiana-two-to-three
description: 使用 Tiana 创建从备孕到生产的双人陪伴应用，包含爸爸妈妈的阶段清单、留言和鼓励。用户说“宝爸备孕 app”“备孕清单”“从两个人到三个人”时使用。
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.2.0"
  parent: tiana
  source: https://github.com/tianacloud/agent-skills/tree/main/skills/tiana-two-to-three
---

# 从两个人，到三个人

使用本 Skill 的 [完整应用模板](assets/app/src/main.js)、[52 周计划](assets/app/src/week-plans.json)、[界面](assets/app/src/markup.html)、[样式](assets/app/src/style.css)和 [SQLite 表结构](assets/app/schema.sql)。模板提供备孕 12 周与孕期 40 周逐周不同的双人清单、角色筛选、留言与鼓励；双方称呼可在应用内修改并保存到 SQLite。首次打开只呈现任务建议和写下第一句话的引导，个人记录由用户自己创建。

## 创建与发布

1. 加载已安装的 `tiana` 和 `tiana-sqlite`。已有可用版本就直接使用，不把重复安装放进用户的创建流程。按 `tiana` 的应用流程完成登录、实例检查和数据库选择。
2. 将本 Skill 的 `assets/app/` 复制为独立应用源码。按用户要求调整文案和名称，将 `tiana app create NAME --json` 返回的 `data.app_id`（或已核实的已有 App ID）填入 `public/tiana.app.json`，保留界面层级、视觉 token 与交互。依照 `tiana/references/csr-apps.md` 使用平台固定 HTML 入口。
3. 在选定的 Tiana SQLite 实例执行 `schema.sql`。它创建旅程阶段、任务完成记录和留言表，并初始化备孕第一周；每周任务建议从 `src/week-plans.json` 加载。更新 `public/tiana.app.json` 中的真实数据库实例 ID，先按 `tiana-sqlite` 的 JavaScript 应用说明使用已发布的 `@tianacloud/serverless@0.1.0-beta.1`。然后运行 `npm ci`、`npm run build`。
4. 按 `tiana/references/source-releases.md` 将源码、锁文件和 SQL 保存到 Tiana Git，确认发布引用指向当前提交，再发布匹配的托管构建。既有外部仓库按该流程确认托管范围。
5. 报告本地开发地址或已发布的应用链接、数据库实例、Tiana Git 仓库与源码提交。

模板的每次任务更新和留言提交都通过 `window.tiana.connection()` 与参数化 SQL 写入 Tiana SQLite；数据库连接失败时显示错误，不把本地预览存储带入正式应用。进一步调整阶段内容时，阅读[内容与交互说明](references/product.md)。
