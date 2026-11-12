# WorkBuddy Connector

The current Connector is built from `packaging/workbuddy/tiana-cloud` and the
canonical Skills. It connects to online:
`https://console.tianacloud.com`.

`cli.json` injects that origin through `env`, installs the latest public
`@tianacloud/cli`, logs in with `tiana login --no-open`, checks `tiana status`,
and signs out with `tiana logout`. `authWaitForExit` keeps login running until
browser approval completes. `authUrlDomain` identifies the online Console.
macOS and Linux use `npm` / `tiana`; Windows uses `npm.cmd` / `tiana.cmd`
to select the npm command shims explicitly. WorkBuddy manages Node.js 22 or newer;
npm installs the matching native platform dependency. Keep optional
dependencies enabled. Tiana Git operations additionally require native Git.
The declared minimum WorkBuddy version (4.24.0) covers these fields and localized
metadata; their meanings are documented by [WorkBuddy](https://open.workbuddy.cn/docs/connector).

Use CLI 1.0.17 or a newer stable release. On first use in a session, Skills check
the installed CLI and npm updates. Missing or below-baseline CLI installations
may be repaired automatically. Other CLI and Skills upgrades require user
confirmation of the package and target version before installation; declining
or leaving the prompt unanswered keeps the installed versions. Skills upgrades
replace existing instructions and add newly shipped skills. Respect the CLI's
should_notify reminder flag as described in the shared update workflow. CLI
upgrades must use the active managed Node/npm installation and prefix. A full Skills installation updates existing
skills and adds every skill shipped in the new package; verify host loading
after reload. See [Connector and host updates](../skills/tiana/references/connector-updates.md).

Status uses the existing account and quota command. A successful result contains
`Quota period:`; a login, network or quota-query failure makes the status check
fail. In particular, quota unavailability does not imply credentials were deleted.

## npm connectivity

If initialization or an update cannot reach `https://registry.npmjs.org/`, report
the actual error and check connectivity from WorkBuddy's managed Node/npm
environment with `npm ping --registry=https://registry.npmjs.org/` (`npm.cmd` on
Windows). Corporate proxies or firewalls may block the registry. Check the host
proxy and npm proxy/https-proxy configuration, and ask the network administrator
to allow the registry and configure the required trusted CA. Redact proxy
credentials from diagnostics; keep certificate verification enabled and retain
the configured registry. Retry initialization after connectivity is restored.
For update failures, follow the shared workflow's conditions for continuing
with the installed versions. This failure does not establish a Tiana login issue.

## Build and verify

```sh
npm ci
npm run validate:ci
npm run test:installer
npm run test:release
./scripts/workbuddy_packaging
TIANA_TEST_CLI_BINARY=/absolute/path/to/tiana npm run test:connector-auth
```

`./scripts/workbuddy_packaging` prepares dependencies and writes
`dist/workbuddy/tiana-cloud-<version>.zip` and its SHA-256 file. The Connector
ZIP has `connector-meta.json`, `cli.json`, `icon.png` and `skills/` at its root.
The script prints the Connector ZIP absolute path last. The Connector installs
CLI through npm; it does not bundle a native CLI binary.

When publishing substantive Skills changes to npm, notify the WorkBuddy platform
of both the Skills and Connector version numbers and submit the corresponding
Connector ZIP for review. Include those versions and the review changes in the
submission notes.

The process fixture runs the real CLI against a local HTTP fixture, exercising
delayed approval, status, quota failure, logout and cancellation. It does not
establish acceptance in the WorkBuddy client or against online services.

Before submitting the ZIP, import it in the supported WorkBuddy client and
verify installation, browser approval, reconnection after restart, logout and
the billing-app conversation. Check that both Connector-managed commands and
chat-issued CLI/Git commands receive the online origin. Verify the hosted app
and a SQLite read/write through the actual online Endpoints. Record the client,
CLI and Skills versions and the actual result of each step.
