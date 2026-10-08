# WorkBuddy Connector

The current Connector is built from `packaging/workbuddy/tiana-cloud` and the
four canonical Skills. It connects to online:
`https://console.tianacloud.com`.

`cli.json` injects that origin through `env`, installs the latest public
`@tianacloud/cli`, logs in with `tiana login --no-open`, checks `tiana status`,
and signs out with `tiana logout`. `authWaitForExit` keeps login running until
browser approval completes. `authUrlDomain` identifies the online Console.
The declared minimum WorkBuddy version covers these fields and localized
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
