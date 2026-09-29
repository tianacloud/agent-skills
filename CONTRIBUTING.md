# Contributing

Edit only the canonical copies under `skills/`. WorkBuddy ZIP files are generated
from those sources and must not be edited or committed.

When product behavior changes, update the smallest relevant reference and keep
the status of preview interfaces explicit. A draft specification is not evidence
that an API is available.

Before opening a pull request, run:

```sh
npm ci
npm run validate:ci
```

To inspect WorkBuddy packages locally:

```sh
npm run build:workbuddy
```

## Distribution and integration maintenance

The following workflows build this skill repository’s distribution packages.
Application projects use the instructions in the installed skills instead.

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

The directories under `skills/` are the canonical source. Edit them first and
generate distribution archives from them; installed copies and generated ZIPs
are not separate instruction sources. npm and portable plugins read `skills/`
directly. WorkBuddy builds copy those same files and add localized metadata
from `packaging/`; they do not maintain another set of skill instructions.

```sh
npm ci
npm run validate:ci
npm run build:workbuddy
npm run build:connector
```

The ledger, notebook and calendar templates have SQLite/SDK and browser fixtures.
With Node.js 22.13+ and Chromium installed (`npx playwright install chromium`),
run `npm run test:apps`. These tests build isolated source repositories, use the
published SDK against in-memory SQLite, and exercise browser editing and save
recovery. They do not provision or validate a deployed Tiana service.

For an isolated process-level auth scheduling test, point
`TIANA_TEST_CLI_BINARY` at a locally built CLI and run `npm run test:connector-auth`.
It uses a loopback fixture and a temporary credential directory, waits more
than 10 seconds before approval, and checks restart status/logout/cancellation.
It neither opens the browser nor proves WorkBuddy's own scheduling behavior.

The source skills follow the [Agent Skills specification](https://agentskills.io/specification).
The root `plugin.json` follows [Agent Plugins v1](https://agent-plugins.org/specification).
