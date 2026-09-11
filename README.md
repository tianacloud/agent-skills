# Tiana Agent Skills

Agent Skills that help coding agents build with Tiana Cloud, a serverless data
App platform whose first supported database engine is SQLite.

## Skills

### `tiana`

Start here for Tiana Cloud. Create and inspect instances, understand lifecycle
states, and manage one-time InstanceToken credentials.

### `tiana-sqlite`

Connect to Tiana SQLite with the current Tiana CLI or Rust transport SDK. Covers
Endpoint URLs, safe Token delivery, Hrana HTTP/WebSocket profiles, and project
integration choices.

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

The proposed WorkBuddy Connector and MCP Server architecture is documented in
[`docs/workbuddy-connector-mcp.md`](docs/workbuddy-connector-mcp.md).

## Development

```sh
npm ci
npm run validate:ci
npm run build:workbuddy
```

The source skills follow the [Agent Skills specification](https://agentskills.io/specification).
The root `plugin.json` follows [Agent Plugins v1](https://agent-plugins.org/specification).

## License

MIT
