import { createTianaFetch } from '@tianadb/serverless';

export const arg = (value) => {
  if (value === null) return { type: 'null' };
  if (Number.isInteger(value)) return { type: 'integer', value: String(value) };
  if (typeof value === 'number') return { type: 'float', value };
  return { type: 'text', value: String(value) };
};

export async function sql(statement, values = []) {
  const auth = window.tiana.auth;
  if (typeof auth?.getAccessToken !== 'function') throw new Error('Tiana 账号鉴权未就绪');
  const connection = await window.tiana.connection();
  if (connection.sql_api !== 'hrana-v3') throw new Error('当前数据库连接不支持此应用');
  const fetchSQL = createTianaFetch({
    origin: connection.origin,
    auth,
    requestBodyMode: 'buffered',
  });
  const response = await fetchSQL(`${connection.origin}/v3/pipeline`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ requests: [
      { type: 'execute', stmt: { sql: statement, args: values.map(arg), want_rows: true } },
      { type: 'close' },
    ] }),
  });
  if (!response.ok) throw new Error('数据库操作结果未知，请刷新查看当前数据');
  const body = await response.json();
  const first = body.results?.[0];
  if (first?.type === 'error') throw new Error('数据库拒绝了本次操作');
  if (first?.type !== 'ok' || first.response?.type !== 'execute') {
    throw new Error('数据库操作结果未知，请刷新查看当前数据');
  }
  const result = first.response.result;
  return {
    rows: (result.rows || []).map((row) => Object.fromEntries(
      result.cols.map((column, index) => [column.name, row[index]?.value ?? null]),
    )),
    affectedRows: Number(result.affected_row_count || 0),
  };
}
