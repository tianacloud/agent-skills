# Management CLI — 0.2.0 preview

These commands ship in `@tianacloud/cli@0.2.0`. They require the matching MGR
deployment, including the CLI account and refresh-expiry response fields.

## Commands

Place a positional ID immediately after `get`, `update` or `resume`, then flags.
Use `--json` for agent calls. Replace example IDs with complete returned IDs.

```sh
tiana auth status --json
tiana instances list --page 1 --page-size 20 --json
tiana instances get INSTANCE_ID --json
tiana instances create --name demo --json
tiana instances update INSTANCE_ID --name renamed --json
tiana requests list --json
tiana requests get REQUEST_ID --json
tiana requests resume REQUEST_ID --json
```

`instances list` accepts page >= 1 and page-size 1..20 (defaults 1 and 20).
Use the returned list pagination to continue; don't decide that a name is
unique before inspecting relevant pages.

`instances create` requires `--name`. It creates SQLite with a `production`
root branch and `timeline=false`; no engine or branch-selection flags are
needed. Optional flags: `--labels '{"env":"dev"}'` (string-valued JSON object),
`--notes 'text'`, `--idle-timeout-ms 60000` (1000..86400000), and `--request-id UUID`.
If idle timeout is omitted the service default applies. The CLI generates a
request UUID when omitted and journals the request before sending it.

`instances update ID` accepts those metadata/config flags, but not request-id.
Labels replace the whole map; `{}` clears labels and `--notes ''` clears notes.
The CLI reads the current revisions before applying the requested update.
On a conflict, read back the instance and resolve the user's intended change;
do not force stale data over a concurrent edit.

After explicit approval to add or replace an instance credential:

```sh
tiana credentials create --instance INSTANCE_ID --name cli --json
```

`--instance` is required. `--name` defaults to `cli`.
`--expires-at` accepts a future `YYYY-MM-DDTHH:mm:ss.SSSZ` value and defaults to
`9999-12-31T23:59:59.999Z` (no lifetime limit). `--request-id UUID` is optional.
The CLI saves the Token and selects it for that instance; it never returns the
raw value in command output. Do not invent list/revoke CLI subcommands.

`auth login [--no-open] [--json]` starts the existing browser Auth Transaction
and waits up to 240 seconds. WorkBuddy runs it with `--no-open` and opens the
printed URL itself. `auth status` is a local read-only check: plain output is
exactly `Logged in` or `Not logged in`, not a live service reachability test.
`auth logout --json` clears the current account's local login and registered
instance credentials and attempts remote logout; request metadata remains.
Do not log out merely to diagnose SQL connectivity.

## Results and recovery

JSON uses `{"status":"succeeded|pending|unknown|failed","data":...,"error":...}`.
Errors carry `code`, `message`, `next_action` and available `request_id`,
`instance_id`, `operation_id`, `token_id`. A failed/pending result can also have
useful `data`: preserve those identifiers when reporting partial completion.

| Exit | Meaning and next step |
| --- | --- |
| 0 | Inspect successful data. Creation is ready for SQL only when `credential_saved=true`. |
| 1 | Known failure. Follow its specific code; don't repeat a write solely because it failed. |
| 2 | Invalid input. Correct the requested arguments. |
| 3 | Pending. Use the original `requests resume REQUEST_ID --json`. |
| 4 | Outcome unknown. For journaled create/credential tasks, inspect and resume the original task; for SQL, use read-only verification. |
| 5 | Management authorization required. Reconnect, then resume the original task as the same account. |

Each business command is bounded to 25 seconds. A new chat or lost command
output is not evidence that nothing happened. `requests list/get` reads the
current account's local journal. Match the task's original input and existing
IDs; do not resume an unrelated task or edit journal files. `resume` continues
the original Operation and credential request instead of making a new instance.

`TOKEN_SECRET_UNAVAILABLE`: the instance/Token may exist but the original secret
cannot be recovered. Explain this partial success. Only after approval, issue
and save a replacement with `credentials create` for the existing instance.
`CREDENTIAL_SAVE_FAILED`: restore local credential-store access, then resume
the original request. Do not ask the model to recover the Token from files.
`LOGOUT_REMOTE_UNKNOWN`: local cleanup succeeded but remote logout is uncertain;
report that distinction without claiming remote revocation succeeded.
