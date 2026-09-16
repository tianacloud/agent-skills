# Tiana Agent Skills

Agent Skills that help coding agents build with Tiana Cloud, a serverless data
App platform whose first supported database engine is SQLite.

Version 0.2.0 in this branch is an unpublished preview. The distribution
examples below apply after the corresponding artifacts are published.

## Skills

### `tiana`

Start here for Tiana Cloud. Create and inspect instances, understand lifecycle
states, and manage one-time InstanceToken credentials.

### `tiana-sqlite`

Connect to Tiana SQLite with the current Tiana CLI or Rust transport SDK. Covers
Endpoint URLs, safe Token delivery, Hrana HTTP/WebSocket profiles, and project
integration choices.

The 0.2.0 preview adds direct CLI SQL, typed parameters, schema inspection and
DDL/CRUD. Management and SQL skills use the CLI's local credential storage;
they do not read or inject Token values.

### `tiana-branches`

Plan around Tiana's preview database-branch lifecycle. This skill includes the
current design-only Control API proposal and does not present it as a released
or callable public API.

## Install

Install all skills from GitHub with a compatible Agent Skills client:

```sh
npx skills add tianacloud/agent-skills
```

Pi users can install the npm package after it has been published:

```sh
pi install npm:@tianacloud/agent-skills
```

The repository root is also an Agent Plugins v1 package. Clients that support
the portable plugin format discover the immediate children of `skills/`.

### Doubao and other directory-based clients

Import the desired directory under `skills/`, preserving its `SKILL.md` and
`references/` files together. If the client accepts ZIP uploads, zip one skill
directory with `SKILL.md` at the archive root.

### WorkBuddy

WorkBuddy marketplace uploads require additional localized metadata. Generate
one ready-to-upload archive per skill:

```sh
npm ci
npm run build:workbuddy
```

The archives are written to `dist/workbuddy/` and are not committed.

### WorkBuddy CLI Connector (0.2.0 preview)

```sh
npm run build:connector
```

This creates `dist/workbuddy/tiana-cloud-0.2.0.zip` and its SHA-256. The ZIP
contains CLI installation/auth configuration and the two canonical skills
`tiana` and `tiana-sqlite`; it does not bundle the native CLI tarball.
The configured download URL is a release target, not yet a published artifact.
See [platform handoff](docs/workbuddy-platform-handoff.md) for U-02 and remaining
installation prerequisites. A generated ZIP is not a verified Connector install.

The agreed CLI + Skill design is in
[`docs/workbuddy-connector-mcp.md`](docs/workbuddy-connector-mcp.md).

## Development

```sh
npm ci
npm run validate:ci
npm run build:workbuddy
npm run build:connector
```

For an isolated process-level auth scheduling test, point
`TIANA_TEST_CLI_BINARY` at a locally built CLI and run `npm run test:connector-auth`.
It uses a loopback fixture and a temporary credential directory, waits more
than 10 seconds before approval, and checks restart status/logout/cancellation.
It neither opens the browser nor proves WorkBuddy's own scheduling behavior.

The source skills follow the [Agent Skills specification](https://agentskills.io/specification).
The root `plugin.json` follows [Agent Plugins v1](https://agent-plugins.org/specification).

## License

MIT
