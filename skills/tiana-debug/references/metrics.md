# Daily inspection

Check data freshness and scrape health before interpreting business metrics. Inspect recent user ingress failures, cold and hot connection latency, task failures and loaded-task age, Agent pool and density, storage errors, node resource pressure, and Collector/Loki/Tempo health. Check exporter queue occupancy and enqueue-failure rates as well as receiver and send failures: a full queue can lose telemetry before an export attempt. The report includes node available-memory ratios and Collector log/span export-failure rates. Memory ratios have no automatic business threshold. Use Grafana for visual trends and the `inspect` command for repeatable checks.

Collector receiver-refused, exporter-send-failed and enqueue-failed counters can first appear with a nonzero value: the deployed Collector records them when an error occurs. A missing series alone cannot distinguish no recorded failure from missing telemetry. Check current target health, accepted/sent data and queue size/capacity alongside the raw failure counter; retain the inspection's incomplete state when evidence is insufficient. A rate can also remain zero after the first failure when there was no earlier zero sample. The corresponding alerts cover the first observed nonzero counter and later increases over their five-minute window.

For `scrape_up`, `inspect` compares recent samples with Prometheus's current active target list. A retired Pod's historical samples remain in the evidence file but do not make the current target coverage incomplete; an active target without a recent sample still does.

`inspect` samples recent Loki logs and Tempo traces, then counts App abnormal exits and Agent-container storage failure events over the requested window. It also reads each active App's latest five-minute `storage.stats` sample for pending upload tasks and bytes; a nonzero backlog is a finding. Event counts can be idle with no matching events, and storage samples can be idle when no App has emitted one recently. A failed backend query is incomplete evidence. Storage searches select the Agent container so Loki's own query logs cannot match the search text and create a false incident.

The published SQLite cold-start acceptance gate uses at least 100 samples measured from Gateway's first received client byte to the first byte of a successful first SQL response; p95 must be at most 200 ms. An online latency chart or Gateway's upstream-first-byte metric is not that benchmark. Hot p99, Git establish, recovery time and density are monitored without invented numerical SLOs.

With `inspect --cluster`, metrics cover that cluster and the shared platform services in its environment. Platform MGR, Gateway and Collector series have no cluster label; they describe the shared service, not traffic attributed to the selected cluster. Series from other named clusters are excluded. Storage-failure and App-exit event counts select the requested cluster after parsing log fields; environment-wide inspection includes all clusters.

Request ID and tenant/instance/branch IDs belong in logs and traces, not Prometheus series labels. If a target is absent, report missing telemetry. If a rate has no denominator, report no applicable traffic. A zero value with a live target is distinct from either case.

## Cold and hot timing

The current implementation adds `tiana_gateway_establish_duration_seconds` (admission entry through final authorization and Agent socket handshake), `tiana_gateway_fetch_duration_seconds` (App response headers and relay completion), and `tiana_gateway_stage_duration_seconds` (parse, policy, directory, control, locate, agent). Verify the target's deployed version and actual series: an unpublished producer is missing evidence, not an idle healthy service.

`inspect` queries cold/hot establish p50/p95/p99, Fetch p99 by activation type and transport/protocol, and stage p95. These observations have no invented business threshold. Stage intervals can overlap, so do not add their quantiles. HTTP/1 Fetch completion means handed to the HTTP server, not received by the client. App HTTP errors do not reveal SQL errors encoded inside a successful HTTP body.

`no_samples` means recent series have no finite numeric sample (for example NaN from an idle histogram); `partial` means only part of the series has usable recent data. Both remain incomplete. Preserve the raw series and query in the evidence bundle. They do not prove a telemetry outage or healthy latency.

`inspect` reports a nonzero `tiana_runtime_agents_failed` value with its node identity, even when other slots remain PARKED. Missing failure-slot data remains incomplete evidence; successful backend queries alone do not establish a healthy pool.

## Loaded work

`loaded_tasks`, `oldest_loaded_task_age` and `loaded_task_snapshot_age` describe process-local observations. MGR counts jobs delivered to tenant actors, including retry waits. Control counts Operation workers retained through result handoff. Support counts loaded collaboration workflows, including waiting for customers or engineers. Mailboxes and unloaded durable work are excluded; overlapping owners during handoff can each report a loaded workflow.

Age starts at the current process loading the work and restarts after process recovery; it is not durable submission age. Snapshot age shows the time since the observed Actor callback update. These values have no automatic stuck-task threshold. Missing series remain incomplete evidence; use task identity and terminal events to diagnose specific work.
