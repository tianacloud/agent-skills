---
name: tiana-whiteboard
description: 使用 Tiana 创建可协作的白板应用，包含便签拖拽、编辑、画笔、连线、缩放和平移。用户说“白板 app”“团队头脑风暴”“类 Miro 白板”时使用。
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.2.0"
  parent: tiana
  source: https://github.com/tianacloud/agent-skills/tree/main/skills/tiana-whiteboard
---

# 浮岛 · 协作白板

使用 [完整应用模板](assets/app/src/main.js)、[界面](assets/app/src/markup.html)、[样式](assets/app/src/style.css)与 [SQLite 表结构](assets/app/schema.sql)。画布交互代码内置于模板，不需要白板或 Canvas 第三方库。首次打开显示三个可点击的起步方向，也可直接新建空白便签；内容由用户自己创建。

## 创建与发布

相对路径以本 `SKILL.md` 所在目录为基准；跨技能链接指向已安装的 `tiana` / `tiana-sqlite`。客户端将技能分开存放时，按技能目录表定位同名技能，再读取对应文件；依赖未安装时补齐该技能。将 `assets/app/` 复制到技能安装目录及技能仓库检出之外的独立应用项目后，再在应用目录执行 npm、Git 和构建命令。技能来源仓库的 Git remote 不属于该应用。按步骤读取引用资料，无需遍历技能仓库的维护文档或打包目录。

按 [JavaScript 数据库连接](../tiana-sqlite/references/js-sdk.md) 的“核验目标托管环境”判断就绪状态：复用当前目标环境的有效验证结果；未核验不等于未部署，Bootstrap 接口存在也不等于 SQL 已连通。

1. 加载已安装的 `tiana` 和 `tiana-sqlite`，按 `tiana` 的应用流程处理登录、数据库实例和固定 HTML 入口。已有可用基础 Skill 时直接使用。
2. 复制 `assets/app/` 为独立应用源码，将 [gitignore.template](assets/app/gitignore.template) 重命名为 `.gitignore`，在选定的 Tiana SQLite 实例执行 `schema.sql`。将 `tiana web create NAME --json` 返回的 `data.id`（或已核实的已有 App ID）填入 `public/tiana.app.json`，更新名称及真实数据库实例 ID，模板已固定核验过的 `@tianacloud/serverless@0.1.0-beta.1`，直接运行 `npm ci`；需要更换 SDK 时按 [JavaScript 数据库连接](../tiana-sqlite/references/js-sdk.md) 核验实际包并更新锁文件。
3. 模板将便签、连接线和画笔路径分开存入 SQLite。打开同一托管地址的页面每 1.5 秒按白板 ID 读取更新；不同便签的修改分别保存，拖动中的页面保持流畅。保留悬浮工具栏、画布平移缩放与适配、便签直接编辑、快捷键、分享链接弹窗及浅色点阵视觉。
4. 按 [源码发布指引](../tiana/references/source-releases.md) 创建或复用 Tiana Git，保存实际实例 ID 到 `source.json`。提交应用源码、锁文件、SQL、清单与构建配置，再按同一发布指引的“构建时传入源码提交”步骤，在命令工具中核验干净工作树并读取 HEAD，执行 `node scripts/build.mjs <完整提交号>`；[构建脚本](assets/app/scripts/build.mjs)接收该提交号，只向 `dist/tiana.app.json` 写入 Git ID 和完整提交 hash。核对模块、CSS、清单和源码关联字段。验证远端发布引用指向该提交后，再发布对应的托管版本。既有外部仓库按共享流程确认托管范围。
5. 在托管地址用两个窗口打开同一白板：点击侧栏概览、画布和帮助入口；从起步卡或顶部按钮创建便签，拖动、编辑、换色、连线、绘制、平移、缩放和适配画布，再刷新；检查分享弹窗地址可选择，概览数量和另一个窗口应读到变化。报告应用链接、数据库实例、Tiana Git 仓库与源码提交。

阅读[交互与同步说明](references/product.md)了解元素数据与验证重点。同步依赖当前页面持续连接 Tiana SQLite；不要把本地预览的浏览器存储实现带入正式应用。
