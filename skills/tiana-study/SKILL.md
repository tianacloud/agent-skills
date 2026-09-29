---
name: tiana-study
description: 使用 Tiana 创建学习管理应用，包含学习任务、每日完成进度、专注计时和每周学习大盘。用户说“学习管理 app”“学习计划”“专注学习工作台”时使用。
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.2.0"
  parent: tiana
  source: https://github.com/tianacloud/agent-skills/tree/main/skills/tiana-study
---

# 间刻 · 学习管理

使用 [完整应用模板](assets/app/src/main.js)、[界面](assets/app/src/markup.html)、[样式](assets/app/src/style.css)与 [SQLite 表结构](assets/app/schema.sql)，交付有任务、进度、专注记录和真实周统计的应用。视觉沿用深蓝工作台、嫩绿强调色和分层信息布局；用户有明确学习领域或目标时，调整首屏的可选任务建议。

## 创建与发布

按 `tiana-sqlite/references/js-sdk.md` 的“核验目标托管环境”判断就绪状态：复用当前目标环境的有效验证结果；未核验不等于未部署，Bootstrap 接口存在也不等于 SQL 已连通。

1. 加载已安装的 `tiana` 和 `tiana-sqlite`；版本可用时直接使用。按 `tiana` 的应用流程处理登录、数据库实例和固定 HTML 入口。
2. 复制 `assets/app/` 为独立应用源码，将 [gitignore.template](assets/app/gitignore.template) 重命名为 `.gitignore`。将 `tiana web create NAME --json` 返回的 `data.id`（或已核实的已有 App ID）填入 `public/tiana.app.json`，并更新名称和真实数据库实例 ID。在选定的 Tiana SQLite 实例执行 `schema.sql`，确认首屏提供任务建议与专注入口，统计从零开始。
3. 模板已固定核验过的 `@tianacloud/serverless@0.1.0-beta.1`，直接运行 `npm ci`；需要更换 SDK 时按 `tiana-sqlite/references/js-sdk.md` 核验实际包并更新锁文件。应用的任务新增、完成状态和 25 分钟专注记录都通过 `window.tiana.connection()` 与参数化 SQL 存入 Tiana SQLite；周图表从记录计算。
4. 按 `tiana/references/source-releases.md` 创建或复用 Tiana Git，保存实际实例 ID 到 `source.json`。提交应用源码、锁文件、SQL、清单与构建配置，再按同一发布指引的“构建时传入源码提交”步骤，在命令工具中核验干净工作树并读取 HEAD，执行 `node scripts/build.mjs <完整提交号>`；[构建脚本](assets/app/scripts/build.mjs)接收该提交号，只向 `dist/tiana.app.json` 写入 Git ID 和完整提交 hash。核对模块、CSS、清单和源码关联字段。验证远端发布引用指向该提交后，再发布对应的托管版本。既有外部仓库按共享流程确认托管范围。
5. 在托管地址修改显示名称并刷新验证；逐一点击侧边栏四个入口，确认切换到对应的独立视图；在无任务和有任务时分别检查“全部、待完成、已完成”三个筛选，再新增和完成任务、刷新验证；完成一轮专注后刷新检查记录和周统计。报告应用链接、数据库实例、Tiana Git 仓库与源码提交。

需要调整学习领域、任务结构和统计口径时，阅读[内容与数据说明](references/product.md)。
