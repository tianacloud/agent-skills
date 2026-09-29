import { sql, verifiedWrite } from "./db.js";
import manifest from "../public/tiana.app.json";
const scope = manifest.web_id;
function normalize(row) {
  return row
    ? { ...row, pinned: Number(row.pinned) === 1, updated: Number(row.updated) }
    : null;
}
function encode(record) {
  return { ...record, pinned: Number(record.pinned) };
}
export async function get(id) {
  return normalize(
    (
      await sql(
        "SELECT id, title, body, folder, pinned, updated FROM notebook_notes WHERE app_id = ? AND id = ?",
        [scope, id],
      )
    ).rows[0],
  );
}
export function same(actual, expected) {
  if (!actual) return false;
  const left = encode(actual),
    right = encode(expected);
  return ["title", "body", "folder", "pinned", "updated"].every(
    (field) => left[field] === right[field],
  );
}
export async function save(record, isNew = false) {
  const row = encode(record);
  const values = ["title", "body", "folder", "pinned", "updated"].map(
    (field) => row[field],
  );
  const statement = isNew
    ? "INSERT INTO notebook_notes (app_id, id, title, body, folder, pinned, updated) VALUES (?, ?, ?, ?, ?, ?, ?)"
    : "UPDATE notebook_notes SET title = ?, body = ?, folder = ?, pinned = ?, updated = ? WHERE app_id = ? AND id = ?";
  await verifiedWrite(
    async () => {
      const result = await sql(
        statement,
        isNew ? [scope, row.id, ...values] : [...values, scope, row.id],
      );
      if (!result.affectedRows)
        throw new Error("这条记录已不存在，请重新加载。");
    },
    () => get(row.id),
    (actual) => same(actual, record),
  );
}
export async function remove(id) {
  await verifiedWrite(
    () =>
      sql("DELETE FROM notebook_notes WHERE app_id = ? AND id = ?", [
        scope,
        id,
      ]),
    () => get(id),
    (actual) => !actual,
  );
}
export const pageSize = 50;
export async function list(view = "all", query = "", offset = 0) {
  const clauses = ["app_id = ?"],
    args = [scope];
  if (view === "pinned") clauses.push("pinned = 1");
  else if (view !== "all") {
    clauses.push("folder = ?");
    args.push(view);
  }
  if (query) {
    clauses.push(
      "(instr(lower(title), lower(?)) > 0 OR instr(lower(body), lower(?)) > 0)",
    );
    args.push(query, query);
  }
  args.push(pageSize + 1, offset);
  const rows = (
    await sql(
      `SELECT id, title, body, folder, pinned, updated FROM notebook_notes WHERE ${clauses.join(" AND ")} ORDER BY pinned DESC, updated DESC, id LIMIT ? OFFSET ?`,
      args,
    )
  ).rows.map(normalize);
  return { rows: rows.slice(0, pageSize), more: rows.length > pageSize };
}
