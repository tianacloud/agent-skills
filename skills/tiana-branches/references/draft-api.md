# Proposed branch API — design-only

These Control routes are an architecture proposal. They are not released
contracts or public MGR endpoints. Exact payloads, response shapes, status
codes, limits, and public authorization remain to be defined.

| Action | Proposed route | Intended behavior |
| --- | --- | --- |
| Create | `POST /control/v1/create-branch` | Accept family, source ID, target name, optional time selection, and an idempotent command; freeze a generated branch ID. |
| Delete | `POST /control/v1/delete-branch` | Delete by branch ID without backward cascade; distinguish logical completion from resource cleanup. |
| Rename | `POST /control/v1/rename-branch` | Rename by branch ID with expected revision and idempotent command; update only the Control directory. |
| List | `GET /control/v1/list-branches` | Read a bounded page from the persistent branch directory without waking an instance. |
| Get | `GET /control/v1/get-branch` | Resolve a branch by ID, family-local name, or source relationship as eventually specified. |
| Operation query | Reuse the Control lifecycle operation query | Return phase, frozen identities, retry state, and reclamation progress. |

## Expected client behavior

- Treat a create as complete only after the child publication proof and
  directory commit are complete. An accepted or in-progress operation is not a
  usable branch.
- Preserve `operation_id`, `source_branch_id`, and the frozen target
  `branch_id` across retries.
- Delete using a resolved branch ID. Never submit an old name and allow the
  server or client to reinterpret it as a later branch that reused that name.
- Surface logical deletion and retained-resource cleanup as distinct facts.
- Treat an unknown result as an operation to query or resume, not permission to
  issue a new command with a new identity.

## Designing a future public client

Place the eventual developer-facing API at the MGR product boundary rather
than exposing these Control paths directly. The public client should use
tenant-scoped product authentication and project-safe projections. Exact MGR
routes must wait for a released contract; do not derive them mechanically from
the proposed Control paths.

