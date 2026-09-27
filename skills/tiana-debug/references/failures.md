# Reading incomplete evidence

| Observation | Interpretation |
| --- | --- |
| Client has an ID, server has no record | The request may have failed before ingress, telemetry may be missing, or the search window may be wrong. Check client stage and `doctor`; do not infer a server cause. |
| Gateway reports timeout | Inspect the last completed downstream Span and its owner log. A timeout does not prove that an accepted downstream mutation failed. |
| Connection was established, then closed | Use the saved connection Trace ID and close source/direction. A same-resource App event at a similar time is only a candidate unless the binding or process identity matches. |
| Fetch transport completed, but `app_http_status` is 400 or higher | The App returned an error response even though forwarding succeeded. Report the App status and inspect its correlated Trace/logs; the status alone does not identify the underlying cause. |
| Browser body reading was cancelled, but Gateway closed successfully | Gateway may have finished sending before the browser cancelled consumption. Compare the SDK `diagnosisOf(response)` or `diagnosisOf(error)` phase and request ID with the server timeline. Server EOF establishes forwarding completion, not complete browser consumption; a server-only report cannot determine this client cancellation. |
| Git connection closes with `broken_pipe` or a client reset | This describes transport closure. Check the native Git exit status and the exact remote ref or commit before deciding the Git operation failed; clone/fetch may already have completed. Do not retry a mutation based only on its close event. |
| MGR/Control SSE closes with `upstream_closed` or `subscription_closed` | The close is an observation. Correlate a cause with that request or connection Trace; keep errors from other task attempts separate. A task may still recover to success. |
| HTTP 202 succeeded | This is acceptance. Follow the recorded Job/Operation ID and all available attempts for the actual result. |
| Gaia control request | Follow the linked control request result separately from the target Operation. A deployment can succeed while its pause request is rejected with `STATE_VERSION_CONFLICT`; the evidence bundle reports both states and the recorded rejection reason. |
| A task attempt failed, then the linked task completed successfully | Report the failed attempt and the final success together. The request ID report follows linked tasks and displays their terminal states. |
| MGR logs `http.client.failed` for a Control route with HTTP 5xx | The observed failing boundary is Control; MGR recorded the outbound error. Correlate that log's Trace ID with the task attempt and final task state. The 5xx alone does not establish Control's internal cause. |
| No result within seven days | Report the retention boundary. Absence alone cannot prove that a trace existed and expired. |
| Search is saturated or a backend failed | Treat conclusions as partial; the evidence bundle records query window, backend response and truncation. |

Never replace a missing task link with an unbounded account or table enumeration. Query an existing exact object API when its identity is known.

Gateway learns tenant identity from the owner associations returned by Control. An Endpoint Token can resolve instance, branch and Cluster without returning tenant ownership to Gateway; Control and Agent can still record the tenant they know. Treat the missing Gateway field according to that stage's knowledge and correlate the same Trace, rather than attributing it to another request.

A retained `connection.closed` event expands the request search back to its recorded start time, bounded by the profile retention. If the connection began earlier, the bundle retains its close evidence and reports the unavailable establishment window. A Tempo 404 alone does not establish why a Trace is absent. An explicit start outside retention is reported as a clipped query window.

## Authentication transactions

An MGR authentication `transaction_id` connects CLI creation and polling with browser approval/denial and token exchange. Recorded `auth.transaction.denied`, `auth.transaction.expired`, and `auth.token.issued` phases establish the observed terminal states `denied`, `expired`, and `completed`. The evidence retains the request and Trace that recorded that state. A denied authorization is a transaction outcome; it does not establish a component fault.

A client can cancel while waiting between requests. Server evidence may then show only a pending transaction. Preserve the client's cancellation output and the investigation time window; a later cleanup or denial must not be presented as the cause of an earlier cancellation.

## SQLite cancellation and session capacity

CLI `INTERRUPTED` with `outcome=unknown` and `cleanup=unconfirmed` means the client stopped waiting; server execution and rollback are unconfirmed. Preserve the logical connection request ID and the client error together.

For Hrana, a subsequent `STREAM_LIMIT` can reflect an earlier session still holding SQLite's exclusive slot. Check the instance's session TTL and query timeout, the original connection's close timeline, and App events for that exact instance, branch and Cluster. The retained baton can hold the slot until expiry; disconnect alone does not prove immediate release. Record the last rejected request and first successful independent probe, when available. Do not infer a recovery SLO from the configured TTL or replay the cancelled SQL to test recovery.

App errors found only through resource/time matching remain candidates. A Gateway `broken_pipe` or `stream_closed` event does not establish the cause of the App's `STREAM_LIMIT`. When CLI reports `UNCOMMITTED_TRANSACTION` with `cleanup=rolled_back`, preserve that explicit cleanup result and its request ID separately from an unconfirmed cancellation.

Task completion and attempt failure are separate evidence. When a failed Span carries the same owning component, task ID and Cluster as a successful task, the report labels it as a recovered task attempt. A matching Trace ID alone does not establish recovery for another task. The original error and Span remain in the evidence bundle.

An MGR HTTP 202 completion without a task identity linked by the same request ID or Trace is reported as partial asynchronous evidence. The tool does not infer a task ID or failure cause from that gap. For an identified MGR job, missing execution or terminal events in the selected window also produces a partial result. An absent terminal event does not distinguish a pending task from missing telemetry; it is not evidence of success or failure. A complete query result still does not prove every expected application event was emitted.
