import { createTianaFetch } from "@tianacloud/serverless";

let transport;
export function arg(value) {
  if (value === null) return { type: "null" };
  if (Number.isInteger(value)) return { type: "integer", value: String(value) };
  if (typeof value === "number") return { type: "float", value };
  return { type: "text", value: String(value) };
}
async function connection() {
  const auth = window.tiana?.auth;
  if (typeof auth?.getAccessToken !== "function")
    throw new Error("账号连接未就绪，请重新登录后加载。");
  if (!transport) {
    transport = window.tiana
      .connection()
      .then((metadata) => {
        if (metadata.sql_api !== "hrana-v3")
          throw new Error("当前数据库连接不支持此应用。");
        return {
          origin: metadata.origin,
          fetch: createTianaFetch({
            origin: metadata.origin,
            auth,
            requestBodyMode: "buffered",
          }),
        };
      })
      .catch((error) => {
        transport = undefined;
        throw error;
      });
  }
  return transport;
}
export async function sql(statement, values = []) {
  const channel = await connection();
  const response = await channel.fetch(`${channel.origin}/v3/pipeline`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      requests: [
        {
          type: "execute",
          stmt: { sql: statement, args: values.map(arg), want_rows: true },
        },
        { type: "close" },
      ],
    }),
  });
  if (!response.ok) throw new Error("数据库响应未确认，请检查当前记录。");
  const body = await response.json();
  const first = body.results?.[0];
  if (first?.type === "error")
    throw new Error("数据库未完成本次操作，请检查连接或表结构。");
  if (
    first?.type !== "ok" ||
    first.response?.type !== "execute" ||
    !first.response.result
  )
    throw new Error("数据库响应未确认，请检查当前记录。");
  const result = first.response.result;
  return {
    rows: (result.rows || []).map((row) =>
      Object.fromEntries(
        result.cols.map((column, index) => {
          const cell = row[index];
          return [
            column.name,
            cell?.type === "null" ? null : (cell?.value ?? null),
          ];
        }),
      ),
    ),
    affectedRows: Number(result.affected_row_count || 0),
  };
}
// A lost response may follow a committed write. Read this record before deciding its result.
export async function verifiedWrite(action, readRecord, matches) {
  try {
    await action();
  } catch (writeError) {
    let actual;
    try {
      actual = await readRecord();
    } catch {
      throw new Error(
        "保存结果暂时无法确认。请保留当前内容，恢复连接后检查记录。",
      );
    }
    if (!matches(actual)) throw writeError;
  }
}
