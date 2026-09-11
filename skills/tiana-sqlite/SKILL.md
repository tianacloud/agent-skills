---
name: tiana-sqlite
description: Connect applications and SQL shells to Tiana Cloud serverless SQLite. Use when a task mentions Tiana SQLite, a Tiana Endpoint hostname, tiana connect, Turso db shell through Tiana, Hrana HTTP or WebSocket, TIANA_TOKEN, or the tiana-sdk Rust transport. Covers only currently available CLI and Rust SDK connection paths.
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.1.0"
---

# Tiana SQLite connections

Tiana's current database connection layer exposes SQLD/Hrana bytes through a
Tiana Endpoint. Select the path that matches the task:

- For an interactive shell, a one-off SQL statement, or wrapping the supported
  native Turso command, read [CLI connections](references/cli.md).
- For Rust code that needs a transparent asynchronous tunnel, read
  [Rust SDK](references/rust-sdk.md).

## Selection rules

1. Inspect the project language, existing dependencies, and deployment target.
2. Use the CLI for shell access and workflows that already invoke the supported
   Turso CLI grammar.
3. Use the Rust SDK only when the caller needs the RawStream transport and can
   consume the internal Git release.
4. If neither path fits, explain the current support boundary. Do not invent a
   public Node.js, Python, Go, ORM, or direct libSQL package integration.

## Connection invariants

- The logical database host is exactly
  `<endpoint_id>.db.service.internal.tiana.com` over logical HTTPS port 443.
- Supply an InstanceToken, not a Tiana login/MGR session.
- Never place a raw Token in a URL, command-line argument, log, or generated
  source file.
- A completed connection transports an opaque database session. Do not replay,
  reconnect, or retry SQL automatically after the session may have begun.
- Keep Hrana HTTP and Hrana WebSocket as distinct profiles; do not reinterpret
  the tunneled bytes.
