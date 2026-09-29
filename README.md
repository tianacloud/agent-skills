# Tiana Agent Skills

Agent Skills that help coding agents build, publish and maintain applications
with Tiana Cloud, including SQLite connections and source releases in Tiana Git.

## Skills

`tiana` is the shared entry point. Specialist skills are sibling directories,
identify `tiana` as their parent, and can be selected directly for a focused task.
Load detailed references only for the workflow being performed.

Deployment routing belongs to the outer launcher. When needed, the user or
runtime sets TIANA_API_ORIGIN before starting the agent or shell. Skills inherit
that environment for CLI and native Git commands; they do not inject/override
it or carry a management-origin configuration file. Missing or ambiguous origins
are reported to the launcher/user instead of choosing a deployment in the skill.

```text
skills/
├── tiana/                 Application workflow, instances, login and source releases
│   ├── SKILL.md           Entry point and workflow routing
│   └── references/        Application template, publishing and CLI details
├── tiana-sqlite/          SQL, schemas and application database connections
│   ├── SKILL.md
│   └── references/        CLI, JavaScript, shell and Rust workflows
├── tiana-two-to-three/    Pregnancy planning and family journey app starter
├── tiana-study/           Study planning and focus dashboard app starter
├── tiana-whiteboard/      Collaborative whiteboard app starter
├── tiana-ledger/          Personal income and expense ledger
├── tiana-notes/           Autosaving notebook with search and folders
├── tiana-calendar/        Personal calendar and daily agenda
└── tiana-branches/        Database branch design (preview only)
    ├── SKILL.md
    └── references/        Lifecycle model and proposed API
```

### `tiana`

Start here to build and publish a Tiana application, create and inspect instances,
or recover CLI login and saved credentials. The application workflow covers the
fixed HTML template, hash routing, hosted versions and source synchronization to
Tiana Git. Existing external repositories require source-hosting consent;
approved releases keep their hosted version linked to a verified source commit.

### `tiana-sqlite`

Query and connect to Tiana SQLite with the CLI, JavaScript SDK, shell or Rust
transport SDK. Browser connection, protocol selection and result decoding live
here; application packaging and publication live in `tiana`.

The end-to-end candidate uses the current CLI's native SQLite shell, account
login, Git transport and integrated application commands. JavaScript application
SQL uses typed parameters through the documented SDK flow. The old direct CLI
`sql execute` grammar and local first-token-save requirement are superseded.
Install `@tianacloud/cli` from npm; see
[CLI installation](skills/tiana/references/getting-started.md).
Browser application guidance requires the new SDK `auth` interface and a shared
`window.tiana.auth` runtime provider. No static-token or older-version fallback is
provided. Refresh credentials remain with the trusted CLI/runtime, never skills
or browser code. The published `@tianacloud/serverless@0.1.0-beta.1` package has been verified
to include the SDK auth interface. Hosted runtime support is implemented; determine
the target environment’s readiness through the [hosted runtime checks](skills/tiana-sqlite/references/js-sdk.md#核验目标托管环境),
not a historical deployment warning. Distinguish interface presence, a successful
authenticated read, and application acceptance; local preview does not verify hosting.

### Application starters

`tiana-two-to-three`, `tiana-study`, `tiana-whiteboard`, `tiana-ledger`,
`tiana-notes`, and `tiana-calendar` include complete
application templates, SQLite schemas, and guided first screens. They use
`tiana` for source releases and hosting and `tiana-sqlite` for database access.
Use a verified SDK build with the account-auth provider before building them.

### `tiana-branches`

Plan around Tiana's preview database-branch lifecycle. This skill includes the
current design-only Control API proposal and does not present it as a released
or callable public API.

## Install

Skills use the separately installed `@tianacloud/cli` package, which provides
both `tiana` and `git-remote-tiana`. Importing a skill does not install these
commands. Follow [CLI installation](skills/tiana/references/getting-started.md)
in the agent's execution environment. For Windows and WorkBuddy, see
[Git helper troubleshooting](skills/tiana/references/windows-git-helper.md).

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
For application development, import `tiana`, `tiana-sqlite`, and the relevant
application starter.
`tiana-branches` is only needed for database branch design work.

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

## License

MIT
