import { sql, verifiedWrite } from "./db.js";
import manifest from "../public/tiana.app.json";
const scope = manifest.web_id;
function normalize(row) {
  return row || null;
}
function encode(record) {
  return record;
}
export async function get(id) {
  return normalize(
    (
      await sql(
        "SELECT id, title, date, start, end, category, location, note FROM calendar_events WHERE app_id = ? AND id = ?",
        [scope, id],
      )
    ).rows[0],
  );
}
export function same(actual, expected) {
  if (!actual) return false;
  const left = encode(actual),
    right = encode(expected);
  return [
    "title",
    "date",
    "start",
    "end",
    "category",
    "location",
    "note",
  ].every((field) => left[field] === right[field]);
}
export async function save(record, isNew = false) {
  const row = encode(record);
  const values = [
    "title",
    "date",
    "start",
    "end",
    "category",
    "location",
    "note",
  ].map((field) => row[field]);
  const statement = isNew
    ? "INSERT INTO calendar_events (app_id, id, title, date, start, end, category, location, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    : "UPDATE calendar_events SET title = ?, date = ?, start = ?, end = ?, category = ?, location = ?, note = ? WHERE app_id = ? AND id = ?";
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
      sql("DELETE FROM calendar_events WHERE app_id = ? AND id = ?", [
        scope,
        id,
      ]),
    () => get(id),
    (actual) => !actual,
  );
}
export async function list(from, to) {
  return (
    await sql(
      "SELECT id, title, date, start, end, category, location, note FROM calendar_events WHERE app_id = ? AND date >= ? AND date < ? ORDER BY date, start, id",
      [scope, from, to],
    )
  ).rows.map(normalize);
}
