# Getting started with Tiana

## Product flow

1. Open `https://console.service.internal.tiana.com/` from an environment with
   access to Tiana's internal network and DNS.
2. Register or sign in using a method shown by the deployment.
3. Create an instance from the available App types. SQLite deployments commonly
   expose the `sqlite` or `sqld` engine family; use the catalog value returned by
   the current deployment instead of hard-coding one.
4. Save the initial `default` InstanceToken when the create wizard delivers it.
   The raw value appears only once.
5. Form the database hostname from the returned Endpoint ID:

   ```text
   <endpoint_id>.db.service.internal.tiana.com
   ```

6. Use the `tiana-sqlite` skill to select the supported connection path.

## Resource model

An instance is the logical database App. Its public product record includes a
display name, labels, notes, engine, public configuration, Endpoint ID, product
revision, and a projected runtime status.

The Endpoint is stable connection identity. Database traffic goes to Gateway
using the Endpoint hostname and does not pass through MGR.

An InstanceToken authorizes database access to one instance. A product session
authorizes management calls to MGR. Never substitute one for the other.

## Product states

| State | Meaning |
| --- | --- |
| `PENDING` | The product record exists and the platform is preparing or finalizing it. |
| `ACTIVE` | The instance is available for normal product use. |
| `UNKNOWN` | MGR cannot currently provide a trustworthy runtime projection. |
| `FAILED` | Preparation or reconciliation failed; inspect `last_error_code`. |

`desired_state` is the requested target (`ENABLED`, `DISABLED`, or `DELETED`),
while `observed_state` describes the lifecycle fact projected from Control.
Do not claim success from `desired_state` alone.

An idle SQLite instance may sleep and wake on the next connection. This is
normal serverless behavior rather than a request to recreate the instance.

## Current public configuration

- `idle_timeout_ms`: `1000..86400000`. If omitted, the SQLite App default is
  30000 ms. Current production guidance normally uses at least 60000 ms.
- `cache_mb`: retained by MGR for client compatibility but ignored by the
  current `app_sqlite` runtime. Do not recommend it as an effective tuning knob.

Instance metadata edits use the quoted product revision as `If-Match`.
Configuration edits additionally carry `expected_config_revision` when a
configuration change is included.

