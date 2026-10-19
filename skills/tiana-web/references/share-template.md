# 将已有 Web App 发布为模板

分享的是可独立安装的材料。发布流程在工作副本中准备材料，最后更新源 Web 的稳定分享链接。

## 1. 核实应用与交付范围

读取 `tiana web publish-share-template --help` 和 `tiana web status-share-template --help`，确认当前 CLI 支持这组命令。读取目标 Web 详情，记录当前租户、真实 Web ID、固定入口、SQLite/Git 绑定和可构建源码位置。取得对应源码，在技能目录之外建立独立工作副本，保留用户原工程和数据。

默认分享源码；根据工程情况可让用户选择「包含源码，允许安装和做同款」或「仅安装，不分享源码」。仅安装仍需准备同份经过公开检查的构建、安装说明、预览和封面。明确 `database_required`：运行需要 SQLite 就填 `true`，纯前端且没有 SQLite 调用就填 `false`；是否有 schema.sql 不能代替这个判断。

完成条件：应用身份、源码选择、SQLite 依赖、真实入口和构建方法都有依据。

## 2. 筛选结构和初始数据

读取已确认关联数据库的 `sqlite_schema`，结合源码整理应用必要的表、索引、视图和触发器，按依赖顺序形成 schema.sql。使用明确列名和筛选条件导出 seed，逐表说明用途：

| 内容 | 初始数据处理 |
| --- | --- |
| 固定分类、单位、枚举、系统字典 | 只保留已核实与个人无关的必要列和记录 |
| 用户、客户、账目、笔记、日程、消息、文件记录、操作历史 | 保留应用必要结构，数据留空；预览另造合成示例 |
| 系统初值和用户自定义内容混合 | 只有可靠区分条件时才导出通用初值 |
| 用途、归属或可公开性不明确 | 提问后再生成 seed |

有疑问时说明表和字段的用途，给出「留空」「合成示例」「仅保留列出的通用初值」供用户选择。问题与报告使用字段名和统计数量，不回显隐私值。分享应用不等于授权分享个人数据；不要直接把整库 dump 当作模板。用户文件默认不带，明确可公开且应用必需的静态素材才能进入材料。

在临时空 SQLite 中依次执行 schema、seed；遇到第一个错误就停止修正。核对行数、主外键、约束及应用首次启动。完成条件：每张 seed 表都有明确的数据来源说明，初始化可在空库成功完成。

## 3. 准备公开副本、预览和封面

根部 metadata.json 填写 name、display_name、description、database_required、可选 schema/seeds 和 variables。应用运行时用 `window.tiana.appId`、`window.tiana.connection()` 和现有账号授权 SDK 取得新安装的上下文。需要在源码或 SQL 中替换的值用 `__TIANA_<名称>_<随机十六进制串>__`，variables 记录全部出现文件。安装 SQL 支持 WEB_ID、SQLITE_INSTANCE_ID、APP_NAME；SQL 占位符优先放在字符串字面量内。

逐项检查源码、依赖锁文件、构建资源、图片、SQL 和展示文案，移除作者的账号绑定、凭据、环境文件、数据库副本、日志、缓存及 Git 管理文件。源码保留重建必需的工程文件；仅安装模式也要检查 JS bundle 和 source map 是否暴露私有内容。

制作 `showcase/preview.html`：复用应用视觉和代表流程，用合成数据和页面内状态实现可操作演示。自包含、压缩前不超过 500,000 字节，能在 `sandbox="allow-scripts"` 且无外部网络的 iframe 内工作。在桌面和手机尺寸实际操作验证，用同份验收预览截图制作 `showcase/cover.webp`。包含源码时另写 `showcase/prompt.md`，说明功能、适用场景、数据模型和可定制点；安装落地页会补充真实分享链接和 CLI 拉取方式。

### 沿用应用图标

首次制作和更新模板都沿用源应用已有图标。检查工程根的 `icon.png`、实际静态资源目录（如 `public/icon.png`），以及应用当前设置的图标；当前应用单独更换过图标时，以该原图为准。源码未带图标时，通过应用现有图标读取入口取得原图，保存到公开副本的静态资源目录，并沿用构建复制流程。

只有确认应用和源码都没有图标时，才按[应用图标](csr-apps.md#应用图标)生成真实 PNG。已有图标读取失败时先解决读取问题，保留复用原图的选择。将选定图片原样用于干净构建根目录的 `icon.png`，核对 `site.tweb` 的 `data/icon.png` 和安装包的 `icon.png` 与该图片一致。

完成条件：公开副本可独立构建，预览可操作，封面来自该预览，图标沿用已确认的原图或在确认缺图后生成，所有材料不含私有数据。

## 4. 打包和发布

1. 在工作副本形成已检查的源码提交，用 `git archive --format=zip --output=/绝对路径/source.zip COMMIT` 导出该提交；从同一提交另取干净目录安装依赖并构建。
2. 使用本技能[打包脚本](../scripts/pack-template.py)，入口和目录取工程实际值：

   ```sh
   python3 /技能实际路径/scripts/pack-template.py --source /绝对路径/source.zip --dist /干净构建目录/dist --entry assets/app.js --output /绝对路径/install.zip
   ```

   用户选择仅安装时增加 `--without-source`。脚本封装 install.json、site.tweb、预览、封面、实际提供的 SQL 和可选源码；它不代替数据和公开内容检查。
3. 复查脚本输出的大小、SHA-256、源码选择及数据库依赖。安装包上限 32 MiB，单材料 16 MiB，所有解析层累计展开 128 MiB、5,000 个条目；site.tweb 同时遵守 16 MiB 和 4,097 条目的 Web 归档限制。超限时先移除无用依赖、压缩资源或精简材料。
4. 执行 `tiana web publish-share-template WEB_ID --file /绝对路径/install.zip --wait --json`。上传峰值包含原模板材料、中转 ZIP 和新材料，全部计入当前租户额度。CLI 申请精确对象授权、直传上传并提交异步发布。
5. 用 `tiana web status-share-template WEB_ID --json` 核对当前 `share.package_id`、Web ID、模板名称和 URL。上传响应未知或等待被中断时先查询该状态；发布失败时检查错误和清理进度，再准备新的发布。发布完成后后台立即清理中转 ZIP，确认删除后释放其占用额度；再次上传时重新申请授权。

完成条件：服务端当前分享指向本次发布的 package_id，才能报告发布成功。交付稳定安装链接、材料摘要、源码选择、数据库结构和 seed 处理说明。链接在应用详情的“分享模板”页可复制，并显示成功安装次数。更新模板沿用该链接；同租户再次安装会复用已安装的应用。

## 撤回和做同款

用户要求撤回时执行 `tiana web withdraw-share-template WEB_ID --json`，再查询状态说明当前分享和清理进度。撤回影响后续安装，已安装应用继续独立使用；重新发布保留链接和累计安装次数。

用户拿分享链接要求做同款时，执行 `tiana web init-share-template LINK --dir PROJECT_DIR --json`。读取回执中的 prompt 和工程 metadata.json，再按[模板初始化](template-init.md)及普通 Web 开发流程创建自己的新应用。没有源码的分享只支持落地页安装。做同款从新工程开始，原模板的安装来源与统计不跟踪这次开发。
