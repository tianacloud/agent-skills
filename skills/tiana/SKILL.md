---
name: tiana
description: Create, inspect and update Tiana Cloud SQLite instances through the Tiana CLI, save instance credentials, and recover interrupted creation tasks. Use for Tiana instance management or WorkBuddy Tiana Connector login and recovery. Use tiana-sqlite for table structure and SQL reads or writes.
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.2.0"
---

# Tiana Cloud

This skill targets the **0.2.0 CLI preview**, published as `@tianacloud/cli@0.2.0`.
Use it with the matching service deployment; Connector availability depends on
your WorkBuddy account. For initial setup, read [Getting started](references/getting-started.md).

## Manage an instance

Read [CLI commands and recovery](references/cloud-cli.md) before invoking
management commands. Use CLI JSON output, not raw management HTTP requests.

1. Inspect `tiana auth status --json` for the account's `principal_id` and
   `tenant_id`. If authorization is needed, guide the user to connect Tiana in
   WorkBuddy; in a terminal, use `tiana auth login`. Do not request passwords,
   browser cookies or Token values.
2. Resolve the requested instance with `instances list/get`. Follow list pages
   when needed; if names are ambiguous, show matching IDs and ask which one.
   Use the full returned instance ID for subsequent commands.
3. For a new instance, run `instances create` once. Completion requires
   `credential_saved=true`; explain partial success without creating another
   instance. For table/schema/data work, use the bundled `tiana-sqlite` skill.
4. For an interrupted creation, inspect `requests list` in a new chat, then
   `requests get/resume` with the original request ID. Do not substitute a new
   create command. Resume only the task that matches the user's intended work.

## Credentials and results

- CLI owns credential storage. Report saved status, IDs and expiry, not secrets;
  do not read its credential files or manually inject a Token into commands.
- A new instance includes its first saved credential. Issuing an additional or
  replacement credential needs the user's explicit request or approval.
- Read [Instances and tokens](references/instances-and-tokens.md) when explaining
  resource identities, one-time Token delivery or management versus SQL access.
- Do not infer completed execution from an exit code alone: inspect `status`,
  `data`, `error.code`, recovery identifiers and `error.next_action`.
