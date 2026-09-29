# Tiana 应用要求

## 入口与路由

使用平台渲染的固定 [index.html 模板](index.html) 和哈希路由。该参考文件与 CLI/Web 的服务端模板一致：服务端先将 `__TIANA_BOOTSTRAP_SCRIPT__` 替换为 `/web/<实际 web_id>/_tiana/bootstrap.js`，再将 `__TIANA_BOOTSTRAP_DATA__` 替换为应用运行时 JSON；浏览器收到的是已完成替换的 HTML。

哈希深链接在直接打开或刷新后也应恢复当前路由；若页面数据需异步读取，应在读取完成后恢复该路由对应的状态。服务端先检查登录会话和应用访问权限，再返回此 HTML。未登录的托管请求跳转到 Console 登录页；授权通过后，文档加载所选版本的 JavaScript 和 CSS。

模板提供 `<div id="app"></div>`。`entry` 指定的模块按正常方式启动并渲染应用。需要数据库连接时，调用 `window.tiana.connection()`；返回的凭据只保存在内存中。加载指示器是临时的，与应用样式隔离。

## 确认账号与数据库

已确认 CLI 具备本流程命令时直接使用。命令缺失时按[开始使用](getting-started.md)安装匹配版本。

1. 复用本轮已完成的账号和额度检查；尚未检查时执行 `tiana status`。需要登录时，按分步登录流程展示链接并确认完成，不读取或输出凭据。
2. 项目已记录且已核实可用的数据库实例 ID 可直接复用，无需列举实例。否则用 `tiana sqlite list/show` 查找；确实没有可用数据库时执行一次 `tiana sqlite create NAME --wait`，保存完整实例 ID。中断后核实原请求和实例，不重复创建。
3. 复用已提供的实际表结构；缺少时执行 `tiana sqlite shell INSTANCE -e "SELECT name, sql FROM sqlite_schema WHERE type='table' ORDER BY name LIMIT 100" --format json`。将表结构和迁移文件保存在项目中。对已核对的 SQL 文件执行 `tiana sqlite shell INSTANCE -f schema.sql --format json`。`-e` 接受一条语句，多语句使用 `-f`。动态数据按 [JavaScript 数据库连接](../../tiana-sqlite/references/js-sdk.md)使用参数化 SQL。
4. 复用项目中已记录、已核实的 App ID；未记录时先用 `tiana web list --json` 查找并核实，重名时依据实际 ID 确认归属；首次创建时执行一次 `tiana web create "应用名称" -m "应用描述" --json`，保存返回的 `data.id`。新 App ID 仅由 MGR 以 9 字节随机值编码为 12 字符 base64url 生成；CLI 不生成或提交 App ID，已有 ID 保持原值；描述为可选元数据（`-m`/`--description`，最多 1024 个 UTF-8 字节），名称仅用于展示，不能用名称推导 ID，不能自行指定 ID。结果未知时保持名称和描述不变，重复同一条 create 命令恢复原请求，不删除待完成记录、不另发创建请求。成功后继续构建、预览或发布时复用该 ID，不重复创建。
5. 在项目和清单中保存非敏感的 App、数据库 ID；清单的 `web_id` 填写实际返回的 App ID。

## 运行时数据库连接

SDK、参数化 SQL 和结果解析按 [JavaScript 数据库连接](../../tiana-sqlite/references/js-sdk.md)处理。应用必须使用支持 `auth` 的 SDK 和 `window.tiana.auth` provider；`window.tiana.connection()` 用于获取连接元信息。共享 provider 和 adapter，不读取 Token 快照，不保留旧 SDK、旧 Bootstrap 或实例 Token 回退路径。

CLI 本地预览优先复用已保存的 CLI 登录，通过一次性本地启动链接授权浏览器；凭据刷新和持久化锁由 CLI/SDK 负责，refresh token 不交给页面。没有可用的已保存账号时才走独立 Console 登录。配套 Web/MGR 托管 Bootstrap 也提供 `window.tiana.auth`，由现有 HttpOnly 登录会话在服务端取得并同步账号授权。账号/租户级 access token 的权限不局限于应用目标实例，业务代码应在相应信任范围内运行。用户要求验证或排查连接故障时，按 [目标托管环境核验](../../tiana-sqlite/references/js-sdk.md#核验目标托管环境)检查实际 provider 和只读 SQL 链路。六个模板常规发布后由用户检查页面；没有运行时验证结果不等于确认缺失，也不代表链路已连通。

凭据只保存在内存，不写入源码、构建产物或浏览器持久存储。skills 不读取 refresh token、不调用刷新接口、不设置管理地址；刷新和授权同步由 SDK/CLI 或运行时代理处理，部署路由由外围环境负责。鉴权失败不自动重放 SQL，写入结果不明时先用独立只读查询核实。

## 构建与清单

输出浏览器可直接执行的 ES 模块、CSS 和资源，资源引用使用相对路径。使用 Vite 库模式时，在 Vite 配置顶层（与 `build` 同级）设置 `define: { 'process.env.NODE_ENV': JSON.stringify('production') }`，并在构建后确认产物没有残留 `process.env.NODE_ENV`。清单路径以实际构建结果为准；例如产物是 `assets/style.css` 时，`styles` 就填写该路径。将清单保存在源码中（例如 `public/tiana.app.json`），由构建自动生成或复制到构建目录；清空构建目录后重建，仍须包含模块、样式和 `tiana.app.json`：

```json
{
  "schema_version": 1,
  "web_id": "ACTUAL_APP_ID",
  "name": "我的账单",
  "rendering": "csr",
  "routing": "hash",
  "entry": "assets/app.js",
  "styles": ["assets/app.css"],
  "database_instance_id": "ACTUAL_INSTANCE_ID"
}
```

关联 Tiana Git 时，构建产物还必须同时含 `git_instance_id` 和 `source_commit`。前者使用实际 Git 实例 ID（`git-...`），后者使用完整的小写 commit hash（40 或 64 位）；具体提交、构建与远端引用核验顺序见[应用源码与版本发布](source-releases.md)。在已提交的源码模板中保存仓库 ID，在命令工具中核验干净工作树并读取 HEAD，再将完整提交号传给构建脚本生成产物的 commit，避免提交 hash 自引用。两字段都省略表示未关联；只填一个会被拒绝。该接口需要配套 CLI/MGR/Console，未部署时明确报告阻塞；更改关联必须发布新版本。

服务端提供 HTML 模板并填入运行时元数据。只上传应用模块、资源和清单。构建路径必须位于构建目录内，不包含 HTML 文件、隐藏文件、符号链接或密钥。清单仍是需要鉴权的元数据，已发布的 JS、CSS 和资源可公开访问。

## 预览与发布

每次发布托管版本时，先按[应用源码与版本发布](source-releases.md)完成源码同步，再上传该源码提交对应的构建产物。

1. 用户需要本地预览时，构建后执行 `tiana web serve --dir DIST --port 4174`，将输出地址交给用户。六个模板常规交付在构建核对后直接进入托管发布。
2. 发布前执行 `tiana status`，需要时完成分步登录。
3. 使用前面已经创建并保存的 App ID，发布新的不可变版本：

```sh
tiana web upload APP_ID --version VERSION_ID --dir DIST --json
tiana web status APP_ID --version VERSION_ID --json
```

上传结果不确定时，仅对完全相同的产物使用同一版本恢复。产物有变化就使用新版本；恢复过程不另建数据库。

4. 报告返回的 `application_url`、应用 ID、版本、数据库 ID、源码仓库和提交。托管地址为 `https://<console-host>/web/<id>/`，入口带尾斜杠，可用 `?version=<version-id>` 固定版本；Console 详情页为 `/console/web/<id>`。托管受阻时，说明具体阻塞原因并提供本地开发地址。创建应用的授权不包含变更服务端部署。

## 应用列表与删除

用 `tiana web list --json` 核对当前账号拥有的 Web 应用，优先使用已保存的真实 ID。用户明确要求删除时，执行 `tiana web delete APP_ID --force`；需要等待源站清理完成时加 `--wait --json`。不得把失败恢复、重新发布或清理本地构建目录当作删除云端应用的授权。

删除会关闭应用入口并清理所有版本和托管文件，关联 SQLite、Git 不随之删除。只收到 `state: deleting` 时报告已受理；收到 `state: deleted` 才报告本次源站清理完成。创建中或任一版本尚未完成上传时直接拒绝删除，应先恢复并完成原操作，不能强制删除。已受理的删除仅可能因分批清理和失败重试延迟完成，不等待上传保护期；公开缓存按缓存策略失效。中断后保留待完成记录，用原 ID 恢复，详情见[CLI 命令](cloud-cli.md)。
