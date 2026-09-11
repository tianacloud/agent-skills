# Branch lifecycle model — design-only

## Identity

| Concept | Proposed meaning |
| --- | --- |
| `branch_id` | Permanent, non-reusable identity for one branch creation. |
| `branch_name` | User-facing name unique within a live family; reusable after deletion. |
| `source_branch_id` | Permanent direct source captured when the branch is created. |
| `operation_id` | Idempotent identity for one normalized create, delete, or rename command. |
| `family` | A set of related branches under one tenant/project, Control authority, and compatible storage domain. |

The proposed first model equates a branch's instance identity with its
`branch_id`; names do not participate in Endpoint, Token, storage, Runtime
binding, pin, or cleanup identity.

## Lifecycle dimensions

Logical branch state:

```text
CREATING -> ACTIVE -> DELETING -> DELETED
```

Resource state is separate:

```text
PRESENT -> RETAINED -> RECLAIMING -> RECLAIMED
```

`DELETED + RETAINED` is a normal result when descendants still depend on the
deleted branch's data. Deletion releases the user-facing name at its logical
commit point; reclamation may finish later.

## Create

The proposed create operation freezes the source ID, a generated child ID, the
target name, and any time selection. The source App/fs layer creates the
snapshot and durable dependency pin. Only after the child proof and Control
directory commit succeed does the child become `ACTIVE` and connectable.

If a response is lost, query or retry the same operation. Do not generate a new
child ID or resample a relative time such as "now".

## Rename and query

Rename and directory reads operate on Control's persistent branch directory.
They do not wake the SQLite instance or ask fs to rename physical storage.
Renaming leaves branch ID, source relation, Endpoint, Token, storage, and
Runtime binding unchanged.

## Delete and reclamation

Delete targets an explicit branch ID and does not recursively delete
descendants. The branch stops admitting new children, settles in-flight work,
logically deletes the target, and later releases source references when safe.
Ancestors can reclaim retained pages only after no live descendant depends on
them.

The initial scope has one source per branch. Merge, multiple parents, backward
cascade deletion, and cross-Control family copying are outside the proposal.

