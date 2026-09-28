# JavaScript applications — HTTP SQL preview

Use this workflow only when the runtime selects `sql_api: "tiana-http"`.
Authentication uses the same mandatory account provider as
[JavaScript applications](js-sdk.md); SQL protocol selection does not change the
authentication mechanism. Use that reference for SDK candidate/release requirements
and hosted runtime readiness. No static-token or old-version fallback is provided.
CLI SQL remains the workflow for inspecting schemas from an agent.

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
`ep-[0-7][0-9a-hjkmnp-tv-z]{25}.db.service.internal.tiana.com`, without paths
or queries. Preserve the returned HTTPS origin including its explicit port;
do not guess a hostname from the instance ID. Localhost and IP literals are rejected. A local
test fixture can inject a custom `fetch` transport while retaining the SDK's
canonical logical origin; do not loosen the production validation.

```js
import { createTianaFetch } from "@tianacloud/serverless";

// The trusted runtime retains refresh credentials; the browser consumes auth.
const auth = window.tiana.auth;
if (typeof auth?.getAccessToken !== "function") {
  throw new Error("Tiana account-auth runtime is not ready");
}
const connection = await window.tiana.connection();
if (connection.sql_api !== "tiana-http") throw new Error("Unsupported SQL API");
const http = createTianaFetch({
  origin: connection.origin,
  auth,
  protocol: "tiana-http",
});
export async function checkDatabase() {
  const response = await http(`${connection.origin}/v1/sql`, {
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

- A shared runtime provider supplies the account access token for outer Gateway
  authorization. A Console cookie is not a Gateway token. Never read CLI credential
  files or expose refresh credentials in the browser. Missing provider support
  blocks use; do not fall back to an InstanceToken.
- Account access has tenant-level permissions; application code must be trusted
  within that account boundary. Keep credentials out of source, build output,
  URLs, logs and browser storage. The CLI/hosted runtime owns login and refresh.
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
