# SQL execution — 0.2.0 preview

Use the matching CLI preview package, which includes the SQL executor.
Send exactly one JSON object on stdin and close stdin at its end. The CLI uses
one connection and one SQL statement per invocation, with a 25-second deadline.
It sends SQL through Gateway to SQLite, not through MGR.

## Input and parameters

```sh
tiana sql execute --instance INSTANCE_ID --input-json - --json <<'TIANA_SQL'
{"sql":"SELECT ? AS message, ? AS count","params":[{"type":"text","value":"你好，O'Reilly"},{"type":"integer","value":"9223372036854775807"}]}
TIANA_SQL
```

This quoted heredoc works in macOS zsh and Bash and suppresses shell expansion.
Replace INSTANCE_ID with the selected full ID. For arbitrary text, use proper
JSON escaping and a delimiter that does not occur as a line in the input, or
use the host's JSON serializer and pipe its output. Never interpolate data
values into SQL or use an unquoted heredoc containing user text.

`sql` is a required nonempty string; `params` is an optional positional array
(default empty). Use `?` placeholders for values. Identifiers cannot be bound:
use inspected names and SQLite double-quote escaping for an identifier.

| Type | Parameter/row cell JSON |
| --- | --- |
| NULL | `{"type":"null"}` |
| Signed int64 | `{"type":"integer","value":"42"}` — decimal string, preserve precision |
| Finite float | `{"type":"float","value":1.5}` |
| Text | `{"type":"text","value":"中文 'quotes'"}` |
| Blob | `{"type":"blob","base64":"AAEC/w=="}` — standard base64 |

Do not send bare JSON strings/numbers/null as cells or encode an int64 as a
JSON number. A column may return different cell types in different rows.

## Inspect schema

```sh
tiana sql execute --instance INSTANCE_ID --input-json - --json <<'TIANA_SQL'
{"sql":"SELECT name, type, sql FROM sqlite_schema WHERE type IN ('table','view') ORDER BY name LIMIT 100","params":[]}
TIANA_SQL

tiana sql execute --instance INSTANCE_ID --input-json - --json <<'TIANA_SQL'
{"sql":"SELECT cid, name, type, \"notnull\" AS is_not_null, dflt_value, pk FROM pragma_table_info(?) LIMIT 100","params":[{"type":"text","value":"notes"}]}
TIANA_SQL
```

## DDL and CRUD

Examples assume the user requested a new `notes` table with these columns.
Inspect existing schema first; do not drop or replace an existing table to make
an example fit. Run each block as a separate command.

```sh
tiana sql execute --instance INSTANCE_ID --input-json - --json <<'TIANA_SQL'
{"sql":"CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL)","params":[]}
TIANA_SQL

tiana sql execute --instance INSTANCE_ID --input-json - --json <<'TIANA_SQL'
{"sql":"INSERT INTO notes (body) VALUES (?), (?) RETURNING id, body","params":[{"type":"text","value":"第一条"},{"type":"text","value":"O'Reilly"}]}
TIANA_SQL

tiana sql execute --instance INSTANCE_ID --input-json - --json <<'TIANA_SQL'
{"sql":"SELECT id, body FROM notes ORDER BY id LIMIT ?","params":[{"type":"integer","value":"20"}]}
TIANA_SQL

tiana sql execute --instance INSTANCE_ID --input-json - --json <<'TIANA_SQL'
{"sql":"UPDATE notes SET body = ? WHERE id = ? RETURNING id, body","params":[{"type":"text","value":"已更新"},{"type":"integer","value":"1"}]}
TIANA_SQL

tiana sql execute --instance INSTANCE_ID --input-json - --json <<'TIANA_SQL'
{"sql":"DELETE FROM notes WHERE id = ? RETURNING id","params":[{"type":"integer","value":"2"}]}
TIANA_SQL
```

Use IDs actually returned by the user's database for update/delete; 1 and 2
above are illustrative. Do not execute every example merely because the user
asked to query a table. An UPDATE/DELETE affecting zero rows is a valid result.
Do not spread BEGIN/COMMIT across commands; they would be different sessions.

## Output and failure interpretation

The outer envelope is `status`, `data`, `error`. Successful data includes
`instance_id`, `endpoint_id`, `columns` (name and optional declared type),
`rows` (arrays of typed cells), `affected_row_count` and `last_insert_rowid`
(decimal string or null). Keep large integer/rowid strings exact. Rows of an
aggregate are not the same as affected rows. Report any cleanup `warning`.

`error` includes `code`, `message`, `next_action`, and, when available,
`database_code` (for example SQLITE_CONSTRAINT). Preserve the database's actual
error rather than inventing an empty successful result.

- `INVALID_INPUT` (exit 2): correct the input or parameter type.
- `SQL_NOT_EXECUTED` (exit 1): the executor knows the SQL was not sent. Fix the
  reported installation/connection/input problem before attempting again.
- `SQL_CREDENTIAL_UNAVAILABLE` / `SQL_CREDENTIAL_INVALID` (exit 1): explain the
  missing or unusable saved Token; get approval for a replacement on this ID.
- `SQL_EXECUTION_FAILED` (exit 1): inspect the database error; change SQL only
  as warranted by the user's request, not by automatic retry loops.
- `SQL_OUTCOME_UNKNOWN` (exit 4): execution may have committed. Read back using
  stable row IDs or the user's business key; never replay the write to find out.
  This includes lost output and some server response/serialization failures.

A successful execute with a close warning remains a known success. Neither
the executor nor the model should turn cleanup into duplicate writes.
