# JavaScript 应用

托管应用使用 `window.tiana.connection()` 和 `@tianadb/serverless` 连接数据库。根据连接返回的 `sql_api` 选择协议：`hrana-v3` 使用下文原生通道；旧 `tiana-http` 应用阅读 [HTTP SQL 预览协议](http-sql-preview.md)。

## 获取 SDK

在应用目录中安装 npm 依赖；已有兼容版本和锁文件时直接使用：

```sh
npm install --save-exact @tianadb/serverless@0.1.0-beta.0
```

将 `package.json` 和锁文件随源码提交到 Tiana Git，克隆后通过包管理器恢复依赖。SDK 包本身不放进应用仓库。安装失败时报告 npm 错误。

## 运行时连接

每次数据库操作先调用 `window.tiana.connection()`，取得 `origin`、`sql_api`、`tianaToken`、实例 ID 和到期时间；Bootstrap 会在需要时更新凭据。凭据只保存在内存，不写入源码、产物、URL、日志或浏览器持久存储。

`sql_api: "hrana-v3"` 使用 SDK 默认原生通道，省略 `protocol`。每次操作发送参数化 execute + close pipeline：

```js
import { createTianaFetch } from '@tianadb/serverless';
async function execute(sql, args = []) {
  const connection = await window.tiana.connection();
  if (connection.sql_api !== 'hrana-v3') throw new Error('Unsupported SQL API');
  const sqlFetch = createTianaFetch({
    origin: connection.origin,
    tianaToken: connection.tianaToken,
    requestBodyMode: 'buffered',
  });
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

## 解析结果

`result.cols` 的每项是 `{name, decltype}`，按 `column.name` 映射行。单元格包含类型：`text` 的 `value` 为字符串，`integer` 为十进制字符串，`float` 为有限数值，`null` 无值，`blob` 使用 `base64`。保留超出 JavaScript 安全整数范围的精度。

同时检查 HTTP 状态和语句错误。响应丢失或格式不完整时，写入结果未知；用独立只读查询核实，不自动重复写入。close 失败与已成功的 execute 分开处理。独立请求之间不共享事务或 TEMP 状态。

每次操作使用最新连接凭据创建 SDK adapter，不长期保留首次 Token。连接凭据签发失败时，报告错误并由用户重新加载或认证。注销不立即撤销已经签发的实例 Token。
