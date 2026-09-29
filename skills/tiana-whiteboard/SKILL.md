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

1. 加载已安装的 `tiana` 和 `tiana-sqlite`，按 `tiana` 的应用流程处理登录、数据库实例和固定 HTML 入口。已有可用基础 Skill 时直接使用。
2. 复制 `assets/app/` 为独立应用源码，在选定的 Tiana SQLite 实例执行 `schema.sql`。将 `tiana web create NAME --json` 返回的 `data.id`（或已核实的已有 App ID）填入 `public/tiana.app.json`，更新名称及真实数据库实例 ID，先按 `tiana-sqlite` 的 JavaScript 应用说明安装已核实支持 `auth` 的 SDK 候选构建并更新锁文件；没有可用构建时报告阻塞。然后运行 `npm ci`、`npm run build`。
3. 模板将便签、连接线和画笔路径分开存入 SQLite。打开同一托管地址的页面每 1.5 秒按白板 ID 读取更新；不同便签的修改分别保存，拖动中的页面保持流畅。保留悬浮工具栏、画布平移缩放与适配、便签直接编辑、快捷键、分享链接弹窗及浅色点阵视觉。
4. 按 `tiana/references/source-releases.md` 将源码、锁文件和 SQL 保存到 Tiana Git，确认源码提交后发布对应构建。既有外部仓库按该流程确认托管范围。
5. 在托管地址用两个窗口打开同一白板：点击侧栏概览、画布和帮助入口；从起步卡或顶部按钮创建便签，拖动、编辑、换色、连线、绘制、平移、缩放和适配画布，再刷新；检查分享弹窗地址可选择，概览数量和另一个窗口应读到变化。报告应用链接、数据库实例、Tiana Git 仓库与源码提交。

阅读[交互与同步说明](references/product.md)了解元素数据与验证重点。同步依赖当前页面持续连接 Tiana SQLite；不要把本地预览的浏览器存储实现带入正式应用。
