---
name: tiana
description: Work with Tiana Cloud, a serverless data App platform currently centered on SQLite. Use when a task mentions Tiana, creating or inspecting Tiana instances, instance lifecycle, Endpoint IDs, the Tiana console or MGR API, or creating, listing, or revoking Tiana InstanceTokens. Route connection implementation to tiana-sqlite and branch planning to tiana-branches.
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.1.0"
---

# Tiana Cloud

Tiana runs database engines as serverless data Apps. The current developer
offering is SQLite: an instance can sleep while idle and wake when a connection
arrives.

## Choose the relevant workflow

- For first use, console setup, instance lifecycle, or Endpoint concepts, read
  [Getting started](references/getting-started.md).
- For instance API calls or InstanceToken lifecycle, read
  [Instances and tokens](references/instances-and-tokens.md).
- For application or shell connections, use the `tiana-sqlite` skill.
- For database branch design, use the `tiana-branches` skill. Branch management
  is preview/design-only and is not a released public API.

## Working rules

- Treat the complete `instance_id`, `endpoint_id`, and `token_id` as opaque
  identities. Do not derive authority or storage locations from their text.
- Use a Tiana product session only with MGR management endpoints. Use an
  InstanceToken only for a database Endpoint; the credentials are not
  interchangeable.
- Preserve the raw InstanceToken returned by a successful create response. It
  is delivered once and cannot later be read or reconstructed.
- Inspect the current project and user goal before proposing changes. Do not add
  an SDK, management API, or preview operation that the task does not need.
- Prefer the console for ordinary product use. Use MGR HTTP examples when the
  user explicitly needs automation or API integration.
