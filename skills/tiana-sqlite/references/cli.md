# Tiana CLI connections

The current self-contained release is `v0.1.0-dev.7` for Linux amd64 and is
paired with Turso CLI `v1.0.32`.

## Install

```sh
curl -O https://console.service.internal.tiana.com/downloads/tiana-cli-linux-amd64-0.1.0-dev.7
curl -O https://console.service.internal.tiana.com/downloads/tiana-cli-linux-amd64-0.1.0-dev.7.sha256
sha256sum -c tiana-cli-linux-amd64-0.1.0-dev.7.sha256

install -d -m 0755 "$HOME/.local/bin"
install -m 0755 tiana-cli-linux-amd64-0.1.0-dev.7 "$HOME/.local/bin/tiana"
tiana verify-install
```

`verify-install` must report `helper-contract=2 mode=embedded`. The download
origin uses Tiana's development private CA. Fix network, DNS, or trust access
rather than disabling certificate verification; there is no insecure mode.

## Connect

With the default `TIANA_TOKEN` environment source:

```sh
tiana connect -- \
  turso db shell https://<endpoint_id>.db.service.internal.tiana.com
```

Run one statement while retaining Turso's native argument position:

```sh
tiana connect --token-file ./tiana-token -- \
  turso db shell https://<endpoint_id>.db.service.internal.tiana.com \
  "SELECT 1"
```

The registered adapter accepts only:

```text
turso db shell <replica-url> [sql]
```

It does not accept Turso Cloud `--instance` or `--location`, a native `--proxy`,
alternate URLs, paths, query strings, fragments, user-info, IP addresses, or a
second locator.

## Token sources

Use one of the Tiana-owned options before `--`:

- default environment variable: `TIANA_TOKEN`
- alternate environment variable: `--token-env NAME`
- current-user-owned mode-0600 file: `--token-file PATH`
- first stdin line: `--token-stdin`

Do not use a raw `--token <secret>` argument. A Token file contains only the raw
47-byte InstanceToken, with at most one final LF or CRLF.

Non-interactive loopback handoff currently requires
`--allow-unisolated-loopback`. Interactive terminals warn and allow the current
loopback handoff by default.

## Profiles and failures

Without `--profile`, the helper classifies the bounded initial request as
`hrana-http` or `hrana-websocket`. Use
`--profile hrana-http|hrana-websocket` only when explicit selection is needed
for diagnosis or controlled integration.

The CLI does not retry or replay a database session after CONNECT succeeds. On
failure after that point, report the result as potentially unknown and let the
caller decide whether the database operation itself is safe to repeat.

