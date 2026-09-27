---
name: tiana-debug
description: Diagnose Tiana requests, connection failures, asynchronous operations, and daily observability health from a request ID or known operation ID. Use for customer incidents and routine inspection in a configured Tiana environment.
license: MIT
metadata:
  author: Tiana Cloud
  version: "0.2.0"
---

# Tiana diagnosis

Use this skill when investigating a Tiana customer report or checking the observability stack. The deterministic queries are in [scripts/tiana_debug.py](scripts/tiana_debug.py). Run `python3 scripts/tiana_debug.py --help` from this skill directory for the current command syntax.

## Before querying

1. Identify the environment and use its **published** Gaia diagnostic profile. Run `doctor` to check Loki, Tempo, Prometheus and Gaia access. A profile contains addresses and datasource IDs, never credentials.
   Loki, Tempo and Prometheus are queried at the internal addresses in that profile; no separate token is needed there. For a Gaia environment that requires its existing API credential, set `GAIA_TOKEN` in the process environment. Do not put the token in the profile or evidence bundle.
2. Obtain the customer's request ID and approximate time when possible. Pass `--since` and `--until` around the reported incident, covering the connection lifetime or asynchronous task through its terminal state. If evidence is missing or the task remains unresolved, widen the window within the 7-day retention period. A default request search starts with the past 24 hours and may scan all 7 days if it finds nothing. For a connection, use the logical connection's request ID. If there is only a task ID, specify its owning component. Control operation IDs also require their Cluster; MGR job IDs are scoped to the environment and use `--component mgr`.
3. Keep the result's completeness state. Empty search results, expired retention, failed backends and truncated searches have different meanings.

## Investigation

- `request` searches logs and traces for the exact request ID, retrieves full traces, correlates exact Trace IDs from standard `traceparent` log fields, follows recorded task links, and writes a local evidence directory. For linked Gaia Operations it also reads current state and paginated stage events; unavailable queries remain explicit evidence gaps. Read its `diagnosis.md` first, then inspect `evidence.json`, `logs.jsonl` and individual traces.
  It also queries known instances in the selected time window, including when the connection Trace succeeded but the application rejected the request. Errors matching the known Cluster, tenant and branch are saved in `resource-candidates.jsonl`; these resource/time matches are candidates, not proof of causation.
- `operation` starts from a known task identity and follows recorded links and attempts. A numeric ID alone is insufficient: specify `--component mgr` for an MGR job or `--component control --cluster <cluster>` for a Control operation. Check its terminal state before treating a failed retry as the final outcome.
- `inspect` checks the fixed daily metrics and live backend status. A missing series is reported separately from healthy idle traffic.

Use [references/architecture.md](references/architecture.md) for component ownership and ID semantics. Use [references/failures.md](references/failures.md) to interpret incomplete evidence and connection failures. Use [references/metrics.md](references/metrics.md) for the daily check and dashboard interpretation.

State a root cause only when a direct failure event or a trace and its correlated log support it. A resource and time match is a candidate, not proof of causation. Report the failed component, observed error, evidence links, missing evidence and next precise query. Do not print credentials, SQL text, Tokens or signed URLs.
