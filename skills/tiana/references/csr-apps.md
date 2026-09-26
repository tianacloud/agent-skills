# Tiana 应用要求

## 入口与路由

使用平台固定的 [index.html](index.html) 和哈希路由。哈希深链接在直接打开或刷新后也应恢复当前路由；若页面数据需异步读取，应在读取完成后恢复该路由对应的状态。服务端先检查登录会话和应用访问权限，再返回此 HTML。未登录的托管请求跳转到 Console 登录页；授权通过后，文档加载所选版本的 JavaScript 和 CSS。

模板提供 `<div id="app"></div>`。`entry` 指定的模块按正常方式启动并渲染应用。需要数据库连接时，调用 `window.tiana.connection()`；返回的凭据只保存在内存中。加载指示器是临时的，与应用样式隔离。

## 确认账号与数据库

已确认 CLI 具备本流程命令时直接使用。命令缺失时按[开始使用](getting-started.md)安装匹配版本。

1. 复用本轮已完成的账号和额度检查；尚未检查时执行 `tiana status`。需要登录时，按分步登录流程展示链接并确认完成，不读取或输出凭据。
2. 项目已记录且已核实可用的数据库实例 ID 可直接复用，无需列举实例。否则用 `tiana sqlite list/show` 查找；确实没有可用数据库时执行一次 `tiana sqlite create NAME --wait`，保存完整实例 ID。中断后核实原请求和实例，不重复创建。
3. 复用已提供的实际表结构；缺少时执行 `tiana sqlite shell INSTANCE -e "SELECT name, sql FROM sqlite_schema WHERE type='table' ORDER BY name LIMIT 100" --format json`。将表结构和迁移文件保存在项目中。对已核对的 SQL 文件执行 `tiana sqlite shell INSTANCE -f schema.sql --format json`。`-e` 接受一条语句，多语句使用 `-f`。动态数据按 [JavaScript 数据库连接](../../tiana-sqlite/references/js-sdk.md)使用参数化 SQL。
4. 在项目和清单中保存非敏感的应用、数据库 ID。

## 运行时数据库连接

SDK、参数化 SQL 和结果解析按 `tiana-sqlite` 技能的 JavaScript 应用流程处理。托管 Bootstrap 提供 `window.tiana.connection()`；每次数据库操作都调用它，以便刷新凭据。凭据只保存在内存中，不写入源码或构建产物。

## 构建与清单

输出浏览器可直接执行的 ES 模块、CSS 和资源，资源引用使用相对路径。使用 Vite 库模式时，在 Vite 配置顶层（与 `build` 同级）设置 `define: { 'process.env.NODE_ENV': JSON.stringify('production') }`，并在构建后确认产物没有残留 `process.env.NODE_ENV`。清单路径以实际构建结果为准；例如产物是 `assets/style.css` 时，`styles` 就填写该路径。将清单保存在源码中（例如 `public/tiana.app.json`），由构建自动生成或复制到构建目录；清空构建目录后重建，仍须包含模块、样式和 `tiana.app.json`：

```json
{
  "schema_version": 1,
  "app_id": "billing",
  "name": "我的账单",
  "rendering": "csr",
  "routing": "hash",
  "entry": "assets/app.js",
  "styles": ["assets/app.css"],
  "database_instance_id": "ACTUAL_INSTANCE_ID"
}
```

服务端提供 HTML 模板并填入运行时元数据。只上传应用模块、资源和清单。构建路径必须位于构建目录内，不包含 HTML 文件、隐藏文件、符号链接或密钥。清单仍是需要鉴权的元数据，已发布的 JS、CSS 和资源可公开访问。

## 预览与发布

每次发布托管版本时，先按[应用源码与版本发布](source-releases.md)完成源码同步，再上传该源码提交对应的构建产物。

1. 构建后执行 `tiana apps serve --dir DIST --port 4174`，保持预览服务运行，将输出的本地开发地址交给用户。
2. 发布前执行 `tiana status`，需要时完成分步登录。
3. 只创建一次归属当前用户的项目，并发布新的不可变版本：

```sh
tiana apps create --project APP_ID --name APP_NAME
tiana apps upload --project APP_ID --version VERSION_ID --dir DIST
```

上传结果不确定时，仅对完全相同的产物使用同一版本恢复。产物有变化就使用新版本；恢复过程不另建数据库。

4. 报告返回的 `application_url`、应用 ID、版本、数据库 ID、源码仓库和提交。托管地址为 `https://<console-host>/web/<app-id>/`，可用 `?version=<version-id>` 固定版本。托管受阻时，说明具体阻塞原因并提供本地开发地址。创建应用的授权不包含变更服务端部署。
