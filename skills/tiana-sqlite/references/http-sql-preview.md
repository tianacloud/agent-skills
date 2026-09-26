# JavaScript applications — HTTP SQL preview

Use this workflow for browser or JavaScript application integration. CLI SQL
remains the workflow for inspecting schemas and executing SQL from an agent.

## Availability and source

The `@tianadb/serverless` source at serverless-js commit
`c846fe5` implements `createTianaFetch` with `protocol: "tiana-http"`.
The inspected package is **private, unreleased**, version `0.1.0-dev.0`.
Do not invent a public npm installation command or assume the installed CLI
contains this JavaScript package. Inspect the application's existing dependency;
otherwise obtain an authorized SDK artifact or a pinned source checkout.

Implementation evidence in the [SDK repository](https://git.service.internal.tiana.com/tiana/serverless-js):
`src/index.ts`, `README.md`, `tests/http-data-interop.mjs` and
`tests/browser-http-data-interop.mjs`. Verify changed interfaces against the
version being used. These tests exercise a Gateway/Agent/App fixture; their
presence does not prove a user's deployed service is ready.

## Request path

The intended browser path is:

```text
Browser application → createTianaFetch → HTTPS Gateway /v1/fetch
                    → SQLite App /v1/sql → SQLite
```

`tiana-http` is a protocol selector inside the SDK request metadata, not a
custom URL scheme. The browser sends ordinary HTTPS. An application backend is
not required for this data path. MGR instance management and CLI login remain
separate from database requests.

The adapter only accepts canonical HTTPS Endpoint origins matching
`ep-[0-7][0-9a-hjkmnp-tv-z]{25}.db.service.internal.tiana.com`, logical port 443,
without paths or queries. Use the returned Endpoint, not an instance ID guessed
into a URL. Localhost, IP literals and alternate ports are rejected. A local
test fixture can inject a custom `fetch` transport while retaining the SDK's
canonical logical origin; do not loosen the production validation.

```js
import { createTianaFetch } from "@tianadb/serverless";

// Supplied by the application's authorized runtime integration.
// Do not replace with a Token literal or a public build-time environment value.
export async function checkDatabase({ databaseOrigin, instanceToken }) {
  const http = createTianaFetch({
    origin: databaseOrigin,
    tianaToken: instanceToken,
    protocol: "tiana-http",
  });
  const response = await http(`${databaseOrigin}/v1/sql`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ sql: "SELECT 1 AS answer;" }),
  });
  const body = await response.json();
  if (!response.ok || body.ok !== true) {
    throw new Error("Tiana SQL request failed");
  }
  return body.results;
}
```

The inspected interop tests read SQL rows from
`body.results[index].result.rows`, with integer cells represented as strings.
Check both HTTP and statement outcomes; do not infer success from HTTP 200
alone. Preserve exact integer values rather than coercing every cell to Number.

## Authentication and user input

- The SDK needs an InstanceToken; a Console cookie or management access token
  is not interchangeable. CLI-owned credentials are not automatically available
  to browser JavaScript. Do not read CLI credential files to bridge this gap.
- A static browser bundle cannot hide a database Token. Keep production Tokens
  out of source, build output, URLs, logs and persisted browser storage. Verify
  the intended user identity and authorized runtime credential-delivery design
  before calling a live database. This SDK does not implement that design.
- The inspected HTTP examples establish `{ sql }` requests. They do **not**
  establish a parameter-binding request contract. CLI typed `params` and Hrana
  requests are different protocols: do not copy their JSON into `/v1/sql` and
  claim compatibility. Locate the SQLite App implementation or verify its
  documented binding contract before enabling live user-input CRUD. Do not
  concatenate form input into SQL as a shortcut.
- Each HTTP call has an independent connection. Separate calls cannot share
  `BEGIN`, TEMP tables or session state. The SDK never automatically retries.
  If a mutation loses its response, use a read-only check before any replay.
- Browser requests require valid certificate trust, CORS and deployed support
  for `tiana-http`. Keep TLS validation enabled.

## Developing while services are unavailable

When the user allows mocks, a local Gateway test double plus persistent SQLite
can validate a browser's CRUD flow. Keep it on loopback, preserve the real SDK
framing boundary, bind values in SQLite, and mark any unverified HTTP parameter
contract as a test-only extension. Keep live writes disabled until that contract
is confirmed. Do not silently fall back to mock after a live request fails.

A local mock does not establish cloud authentication, database provisioning,
cold activation or data isolation.
