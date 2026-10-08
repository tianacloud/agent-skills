# WorkBuddy Connector

The current Connector is built from `packaging/workbuddy/tiana-cloud` and the
four canonical Skills. It connects to online:
`https://console.tianacloud.com`.

`cli.json` injects that origin through `env`, installs the latest public
`@tianacloud/cli`, logs in with `tiana login --no-open`, checks `tiana status`,
and signs out with `tiana logout`. `authWaitForExit` keeps login running until
browser approval completes. `authUrlDomain` identifies the online Console.
macOS and Linux use `npm` / `tiana`; Windows uses `npm.cmd` / `tiana.cmd`
to select the npm command shims explicitly. Node.js 22 is managed by WorkBuddy,
and npm installs the matching native platform dependency. Keep optional
dependencies enabled. Tiana Git operations additionally require native Git.
The declared minimum WorkBuddy version (4.24.0) covers these fields and localized
metadata; their meanings are documented by [WorkBuddy](https://open.workbuddy.cn/docs/connector).

Use CLI 1.0.0 or later. Existing installations must be checked with `tiana version`
and updated through the normal installation flow when necessary. Skills also
check their minimum CLI version before resource operations.

Status uses the existing account and quota command. A successful result contains
`Quota period:`; a login, network or quota-query failure makes the status check
fail. In particular, quota unavailability does not imply credentials were deleted.

## Build and verify

```sh
npm ci
npm run validate:ci
npm run test:installer
npm run test:release
npm run build:connector
TIANA_TEST_CLI_BINARY=/absolute/path/to/tiana npm run test:connector-auth
```

The process fixture runs the real CLI against a local HTTP fixture, exercising
delayed approval, status, quota failure, logout and cancellation. It does not
establish acceptance in the WorkBuddy client or against online services.

Before submitting the ZIP, import it in the supported WorkBuddy client and
verify installation, browser approval, reconnection after restart, logout and
the billing-app conversation. Check that both Connector-managed commands and
chat-issued CLI/Git commands receive the online origin. Verify the hosted app
and a SQLite read/write through the actual online Endpoints. Record the client,
CLI and Skills versions and the actual result of each step.

## Review package verification (2026-10-08)

Checked the current WorkBuddy Connector documentation and public npm registry.
The `latest` CLI is 1.0.0, with native packages for macOS/Windows x64 and arm64,
and Linux x64, arm64 and riscv64. Installed the public package into an isolated
Linux directory and verified `version`, `login --help` and `web --help`.
The online Console returned HTTP 302 and unauthenticated
`/api/v1/auth/transactions/whoami` returned HTTP 401 with normal system CA trust.

All six `validate:ci` stages, four installer tests and five release tests passed.
The authentication process fixture passed against that installed CLI 1.0.0,
including delayed browser approval, persisted login across processes, quota
failure, logout and cancellation. The archive validator checks all three
platform command configurations and compares all packaged Skill resources
against canonical sources.

The submission ZIP is `tiana-cloud-1.0.0.zip`; upload the ZIP, retaining its sibling
SHA-256 file for verification. This package includes all four Skills and their
references, including current Web project/publication and Windows instructions.
Actual WorkBuddy client import, macOS/Windows execution, online browser approval
and end-to-end Web/SQLite operations remain to be verified in the client.
