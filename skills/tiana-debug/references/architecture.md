# Diagnostic identity and component ownership

- A diagnostic `request_id` identifies one user request or logical SQL/Git connection. A retry may have another Trace ID. The business `request_id` used for idempotency is a separate identity.
- `trace_id`/`span_id` link a synchronous execution. A successful connection may close after the establishment Span has ended; close events retain its original identity.
- `tenant_id`, `instance_id`, `branch_id`, and `cluster` record fields known at each stage. Earlier ingress may only know an Endpoint. `cluster` is the owning Control Cluster; node and deployment target are separate placement fields.
- MGR owns tenant and product projection; Directory owns Endpoint to Cluster location; Control owns instance, branch, route and Operation; Runtime owns node Agent pool and binding; Agent owns an App process and connection admission; App/FS owns data and storage failures; Gaia owns deployment Operations; Support owns tickets, deliveries and actions.
- A task link connects a front-end request with an existing Job/Operation or a downstream task. Restarts produce a new execution Trace associated with the persisted task identity. A ticket ID or resource/time match alone does not prove that one message caused another task.
- Control expiry links use the plan's existing instance, branch and expected deletion time, scoped to its Cluster. `expiry_plan_id` records that tuple for log queries. A reset links the old and replacement branch plans through its Operation; a changed expiry has a different plan identity. Expansion requires those recorded links within retention, rather than matching a branch name or guessing from nearby times.

- Social authentication uses its existing `transaction_id` to connect start, callback and registration requests across the provider redirect. The tool expands these MGR records within the selected time window; the link itself does not establish authentication success.

See the deployed environment's current architecture and owner contracts for exact API behavior. The diagnostic profile must come from Gaia's published snapshot.
