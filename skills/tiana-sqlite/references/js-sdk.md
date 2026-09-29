# JavaScript 应用

应用使用 `window.tiana.auth`、`window.tiana.connection()` 和 `@tianacloud/serverless` 连接数据库。根据连接返回的 `sql_api` 选择协议：`hrana-v3` 使用下文原生通道；`tiana-http` 通道阅读 [HTTP SQL 预览协议](http-sql-preview.md)。

## SDK 与运行时要求

应用必须使用支持 `auth: TianaAuthProvider` 的 `@tianacloud/serverless`，以及提供 `window.tiana.auth.getAccessToken()` 的 Bootstrap。两者是必要条件，不保留静态 Token 或旧版本回退路径。

已核验 npm 发布包 `@tianacloud/serverless@0.1.0-beta.1` 的类型声明与实现包含 `TianaAuthProvider`、`auth` 参数和不自动重放的传输，可固定使用该版本。其他构建仍需检查实际类型声明和构建来源，不只凭版本号推断能力。无法取得符合要求的 SDK 时，报告依赖未就绪，不继续生成降级应用；SDK 可用不代表目标托管运行时已部署。

将 `package.json` 和锁文件随源码提交到 Tiana Git，克隆后通过包管理器恢复依赖。SDK 包本身不放进应用仓库，候选构建也不引用其他机器无法访问的临时路径。安装失败时报告实际错误。

## 运行时连接

`window.tiana.connection()` 提供 `origin`、`sql_api`、实例 ID 等连接信息；应用使用共享的 `window.tiana.auth` 获取动态 access token。不要读取或缓存 `connection.tianaToken`，不要向 adapter 传入静态 `tianaToken`，也不要同时传入两种鉴权参数。

access token 具有账号/租户级数据权限，不能把应用目标实例 ID 当作凭据的权限边界。refresh token 留在可信的 CLI/运行时代理中，不进入浏览器。完整权限边界见 [实例与凭据](../../tiana/references/instances-and-tokens.md)。

`sql_api: "hrana-v3"` 使用 SDK 默认原生通道，省略 `protocol`。每次操作发送参数化 execute + close pipeline：

```js
import { createTianaFetch } from '@tianacloud/serverless';
const auth = window.tiana.auth;
if (typeof auth?.getAccessToken !== 'function') {
  throw new Error('Tiana account-auth runtime is not ready');
}
const connection = await window.tiana.connection();
if (connection.sql_api !== 'hrana-v3') throw new Error('Unsupported SQL API');
const sqlFetch = createTianaFetch({
  origin: connection.origin,
  auth,
  requestBodyMode: 'buffered',
});
async function execute(sql, args = []) {
  const response = await sqlFetch(`${connection.origin}/v3/pipeline`, {
    method: 'POST', headers: {'content-type': 'application/json'},
    body: JSON.stringify({requests: [
      {type: 'execute', stmt: {sql, args, want_rows: true}},
      {type: 'close'},
    ]}),
  });
  if (!response.ok) throw new Error('SQL outcome unavailable; do not retry a write');
  const body = await response.json();
  const statement = body.results?.[0];
  if (statement?.type === 'error') throw new Error('Database rejected the statement');
  if (statement?.type !== 'ok' || statement.response?.type !== 'execute') {
    throw new Error('SQL outcome unavailable; verify with a separate read');
  }
  // close 失败不代表 execute 未提交。
  return {result: statement.response.result, cleanupWarning: body.results?.[1]?.type !== 'ok'};
}
// 参数与 SQL 分开；整数用十进制字符串保持精度。
const {result} = await execute('SELECT ? AS description, ? AS cents', [
  {type: 'text', value: "中文 O'Reilly"}, {type: 'integer', value: '12345'},
]);
```

## 共享鉴权 provider

同一页面/登录会话复用运行时提供的 provider，adapter 可长期复用，由 provider 在每次请求前提供有效 access token。不要为每次 SQL 创建新的会话 provider，不在 provider 抛错后降级为静态 Token 重发请求。

CLI 预览在进程内刷新账号凭据，等待授权同步到数据面后再向页面交付 access token；并发调用共享刷新，取消一个调用不取消其他调用的刷新。业务代码只消费 provider，不从浏览器构造含 refresh token 的 `createTianaSessionAuth`，不自行轮询 MGR。`sql_api` 的选择与鉴权方式独立，仍按返回值选择 SQL 协议。

配套 Web/MGR 托管 Bootstrap 已实现同一个 `window.tiana.auth` 接口，以 HttpOnly 登录会话在服务端取得并同步账号授权；浏览器不持有 refresh token。发布前核实目标环境已部署该能力。缺少能力时报告发布阻塞，不切回实例 Token，也不把本地预览成功当作托管鉴权已就绪。

## 刷新与错误恢复

- 正常的 access token 临近到期由 SDK/CLI 处理，skills 不定时刷新、不读取 refresh token、不把管理地址注入应用。`TIANA_API_ORIGIN` 仍由启动 agent/shell 的外围环境按需设置。
- `AUTH_LOGIN_REQUIRED` 或 `AUTH_REFRESH_UNCERTAIN`：报告需重新登录。结果不明的刷新可能已消费旧 refresh token，不能重试旧值。
- `AUTH_PERSIST_FAILED`：在持有会话 provider 的可信宿主中修复凭据存储，再重试保存新凭据；不能恢复旧凭据或重新消费旧 refresh token。
- `AUTH_NOT_READY`：尚未向数据面发送请求，后续可重新检查授权同步。CLI 浏览器代理可能只返回通用授权错误，不保证透传这些 SDK 错误码；按实际接口报告并重新认证，不自行推断刷新已成功。
- Gateway 401/403、网络中断或 SQL 响应不完整，都不触发自动刷新并重放原 SQL。尤其写入可能已经提交，应先用独立只读查询核实结果。

## 解析结果

`result.cols` 的每项是 `{name, decltype}`，按 `column.name` 映射行。单元格包含类型：`text` 的 `value` 为字符串，`integer` 为十进制字符串，`float` 为有限数值，`null` 无值，`blob` 使用 `base64`。保留超出 JavaScript 安全整数范围的精度。

同时检查 HTTP 状态和语句错误。响应丢失或格式不完整时，写入结果未知；用独立只读查询核实，不自动重复写入。close 失败与已成功的 execute 分开处理。独立请求之间不共享事务或 TEMP 状态。

连接凭据获取失败时，报告错误并由用户重新加载或认证。注销不等同于已经交付的 access token 立即撤销。
