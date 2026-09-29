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

相对路径以本 `SKILL.md` 所在目录为基准；跨技能链接指向已安装的 `tiana` / `tiana-sqlite`。客户端将技能分开存放时，按技能目录表定位同名技能，再读取对应文件；依赖未安装时补齐该技能。将 `assets/app/` 复制到技能安装目录及技能仓库检出之外的独立应用项目后，再在应用目录执行 npm、Git 和构建命令。技能来源仓库的 Git remote 不属于该应用。按步骤读取引用资料，无需遍历技能仓库的维护文档或打包目录。

完成构建、清单与源码关联核对后发布到 Tiana，以 CLI 发布状态确认交付。页面交互和实际使用由用户打开托管链接自行检查；本流程不要求 Agent 安装或调用浏览器自动化工具，也不以浏览器验收作为发布前置步骤。

1. 加载已安装的 `tiana` 和 `tiana-sqlite`。已有可用版本就直接使用，不把重复安装放进用户的创建流程。按 `tiana` 的应用流程完成登录、实例检查和数据库选择。
2. 将本 Skill 的 `assets/app/` 复制为独立应用源码，将 [gitignore.template](assets/app/gitignore.template) 重命名为 `.gitignore`。按用户要求调整文案和名称，将 `tiana web create NAME --json` 返回的 `data.id`（或已核实的已有 App ID）填入 `public/tiana.app.json`，保留界面层级、视觉 token 与交互。依照 [应用开发与发布](../tiana/references/csr-apps.md) 使用平台固定 HTML 入口。
3. 在选定的 Tiana SQLite 实例执行 `schema.sql`。它创建旅程阶段、任务完成记录和留言表，并初始化备孕第一周；每周任务建议从 `src/week-plans.json` 加载。更新 `public/tiana.app.json` 中的真实数据库实例 ID，模板已固定核验过的 `@tianacloud/serverless@0.1.0-beta.1`，直接运行 `npm ci`；需要更换 SDK 时按 [JavaScript 数据库连接](../tiana-sqlite/references/js-sdk.md) 核验实际包并更新锁文件。
4. 按 [源码发布指引](../tiana/references/source-releases.md) 创建或复用 Tiana Git，保存实际实例 ID 到 `source.json`。提交应用源码、锁文件、SQL、清单与构建配置，再按同一发布指引的“构建时传入源码提交”步骤，在命令工具中核验干净工作树并读取 HEAD，执行 `node scripts/build.mjs <完整提交号>`；[构建脚本](assets/app/scripts/build.mjs)接收该提交号，只向 `dist/tiana.app.json` 写入 Git ID 和完整提交 hash。核对模块、CSS、清单和源码关联字段。验证远端发布引用指向该提交后，再发布对应的托管版本。既有外部仓库按共享流程确认托管范围。
5. 发布后用 `tiana web status` 核对版本与源码关联字段，交付应用链接、数据库实例、Tiana Git 仓库、发布引用与源码提交，请用户打开应用自行检查。报告“已发布”，不将发布成功表述为交互已验证。

模板的每次任务更新和留言提交都通过 `window.tiana.connection()` 与参数化 SQL 写入 Tiana SQLite；数据库连接失败时显示错误，不把本地预览存储带入正式应用。进一步调整阶段内容时，阅读[内容与交互说明](references/product.md)。
