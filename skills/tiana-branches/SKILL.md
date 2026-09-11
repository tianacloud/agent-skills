---
name: tiana-branches
description: Plan and review Tiana database branch workflows, branch identity, create/delete/rename behavior, and the proposed Control branch API. Use when a task explicitly mentions Tiana branches, branch families, reset-from-parent-style workflows, branch retention, or implementing a future Tiana branch client. This capability is preview/design-only and not a released public API.
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.1.0"
---

# Tiana database branches — preview

Tiana branch lifecycle is a design proposal under review. Use this skill for
product planning, API review, client design, and implementation preparation.
Do not claim that the proposed routes can be called in a current deployment.

## Read by task

- For identity, lifecycle, retention, and workflow semantics, read
  [Lifecycle model](references/lifecycle-model.md).
- For proposed paths and request/response expectations, read
  [Draft API](references/draft-api.md).

## Working rules

- Label commands, examples, and UI plans as preview or design-only.
- Keep `branch_id` as permanent identity and `branch_name` as a reusable label.
- Freeze source and target IDs under the original idempotent operation. A retry
  must continue that operation rather than resolve names again.
- Treat logical deletion separately from physical resource reclamation.
- Do not invent exact JSON fields, error codes, limits, or SDK methods that the
  draft has not frozen.
- If the user wants to execute a branch operation, explain that the public API
  is not released and offer a design or integration plan instead.
