#!/usr/bin/env python3
"""Read-only Tiana incident queries; installed with the tiana-debug skill."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import shlex
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import ProxyHandler, Request, build_opener


UTC = timezone.utc
DAY = timedelta(days=1)
PAGE_LIMIT = 500
TRACE_LIMIT = 100
IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]+$")
TRACE_ID = re.compile(r"^[0-9a-fA-F]{16,32}$")
SECRET = re.compile(
    r"(?i)(authorization\s*[:=]\s*bearer\s+|(?:(?:access_)?token|signature|secret|password)\s*[:=]\s*)[^\s,;&\"']+"
)


class QueryError(Exception):
    pass


class RetentionWindowUnavailable(QueryError):
    def __init__(self, start: datetime, end: datetime):
        super().__init__("Requested window is entirely outside available retention; no historical evidence can be queried")
        self.start, self.end = start, end


def clean(value: str) -> str:
    return SECRET.sub(lambda match: match.group(1) + "[REDACTED]", value)


def clean_fields(value: object) -> object:
    if isinstance(value, str):
        return clean(value)
    if isinstance(value, dict):
        return {key: clean_fields(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_fields(item) for item in value]
    return value


def json_text(value: object, indent: int | None = 2) -> str:
    return json.dumps(clean_fields(value), ensure_ascii=False, sort_keys=True, indent=indent)


def instant(value: str) -> datetime:
    try:
        if value.isdigit():
            return datetime.fromtimestamp(int(value), UTC)
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except (ValueError, OverflowError) as exc:
        raise QueryError(f"Invalid time: {value}") from exc


def ns(value: datetime) -> int:
    delta = value - datetime(1970, 1, 1, tzinfo=UTC)
    return ((delta.days * 86400 + delta.seconds) * 1_000_000
            + delta.microseconds) * 1000


def bounded_windows(start: datetime, end: datetime):
    cursor = start
    while cursor < end:
        stop = min(cursor + DAY, end)
        yield cursor, stop
        cursor = stop


def profile_for(args: argparse.Namespace) -> dict:
    if args.profile:
        path = Path(args.profile).expanduser()
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        path = base / "tiana-debug" / f"{args.env}.json"
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise QueryError(f"Cannot read published Gaia profile {path}: {exc}") from exc
    if profile.get("environment") != args.env:
        raise QueryError(f"Profile environment differs from --env {args.env}")
    for field in ("loki_query_origin", "tempo_query_origin", "prometheus_query_origin"):
        if not str(profile.get(field, "")).startswith("http://"):
            raise QueryError(f"Profile has no internal {field}")
    return profile


class Backend:
    def __init__(self, profile: dict):
        self.profile = profile
        self.queries: list[dict] = []
        self.opener = build_opener(ProxyHandler({}))

    def get(self, backend: str, path: str, params: dict | None = None) -> object:
        origin = self.profile.get(f"{backend}_query_origin")
        if backend == "gaia":
            origin = self.profile.get("gaia_origin")
        if not origin:
            raise QueryError(f"{backend} address absent from profile")
        url = origin.rstrip("/") + path
        if params:
            url += "?" + urlencode(params)
        headers = {"Accept": "application/json"}
        if backend == "gaia" and self.profile.get("gaia_host"):
            headers["Host"] = self.profile["gaia_host"]
        if backend == "gaia" and os.environ.get("GAIA_TOKEN"):
            headers["X-Gaia-Token-Access"] = "1"
            headers["Authorization"] = "Bearer " + os.environ["GAIA_TOKEN"]
        query = {"backend": backend, "path": path, "params": params or {}}
        self.queries.append(query)
        started = time.monotonic()
        try:
            with self.opener.open(Request(url, headers=headers), timeout=20) as response:
                query["http_status"] = response.status
                body = response.read()
                return json.loads(body) if "json" in response.headers.get("Content-Type", "") else body.decode("utf-8")
        except HTTPError as exc:
            query["http_status"] = exc.code
            query["error"] = f"HTTP {exc.code}"
            raise QueryError(f"{backend} HTTP {exc.code} at {path}") from exc
        except (URLError, TimeoutError, ValueError) as exc:
            query["error"] = clean(str(exc))
            raise QueryError(f"{backend} query failed at {path}: {exc}") from exc
        finally:
            query["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)


def attr_fields(line: str, metadata: dict) -> dict:
    fields = dict(metadata)
    try:
        parsed = json.loads(line)
        if isinstance(parsed, dict):
            fields.update(parsed)
    except ValueError:
        plain = re.sub(r"\x1b\[[0-9;]*m", "", line)
        level = re.search(r"\b\d{4}-\d{2}-\d{2}T\S+\s+(ERROR|FATAL)\s", plain)
        if level:
            fields.setdefault("level", level.group(1).lower())
        try:
            for word in shlex.split(plain):
                if "=" in word:
                    key, value = word.split("=", 1)
                    fields[key] = value
        except ValueError:
            pass
    return fields


def log_query(env: str, field: str, value: str, component: str = "",
              cluster: str = "") -> str:
    if field not in {"request_id", "trace_id", "job_id", "operation_id", "collaboration_id", "transaction_id", "instance_id", "expiry_plan_id"}:
        raise QueryError(f"Unsupported log field: {field}")
    query = "{environment=" + json.dumps(env) + "} | json | logfmt | " + field + "=" + json.dumps(value)
    for key, qualifier in (("component", component), ("cluster", cluster)):
        if qualifier:
            query += " | " + key + "=" + json.dumps(qualifier)
    return query


def loki_window(client: Backend, query: str, start_ns: int, end_ns: int,
                records: dict, gaps: list[str]) -> None:
    # Loki's start is inclusive and end is exclusive.
    response = client.get("loki", "/loki/api/v1/query_range", {
        "query": query, "start": str(start_ns), "end": str(end_ns),
        "direction": "forward", "limit": str(PAGE_LIMIT),
    })
    if response.get("status") != "success":
        raise QueryError("Loki returned non-success query status")
    page = []
    for stream in response.get("data", {}).get("result", []):
        labels = stream.get("stream", {})
        for item in stream.get("values", []):
            if len(item) < 2:
                continue
            timestamp, line = str(item[0]), str(item[1])
            metadata = item[2] if len(item) > 2 and isinstance(item[2], dict) else {}
            event = {"time_unix_nano": timestamp, "stream": labels,
                     "fields": attr_fields(line, metadata), "line": clean(line)}
            key = (timestamp, json.dumps(labels, sort_keys=True), line,
                   json.dumps(metadata, sort_keys=True))
            records[key] = event
            page.append(event)
    if len(page) < PAGE_LIMIT:
        return
    if end_ns - start_ns <= 1:
        gaps.append(f"Loki saturated at nanosecond {start_ns}; identical-time events may be missing")
        return
    middle = (start_ns + end_ns) // 2
    loki_window(client, query, start_ns, middle, records, gaps)
    loki_window(client, query, middle, end_ns, records, gaps)


def search_logs(client: Backend, env: str, field: str, value: str,
                start: datetime, end: datetime, gaps: list[str],
                component: str = "", cluster: str = "") -> list[dict]:
    records: dict[tuple, dict] = {}
    query = log_query(env, field, value, component, cluster)
    for left, right in bounded_windows(start, end):
        try:
            loki_window(client, query, ns(left), ns(right), records, gaps)
        except QueryError as exc:
            gaps.append(str(exc))
    return sorted(records.values(), key=lambda event: int(event["time_unix_nano"]))


def resource_failure_candidates(client: Backend, env: str, logs: list[dict],
                                start: datetime, end: datetime, gaps: list[str]) -> list[dict]:
    identities = {tuple(str(record["fields"].get(key, "")) for key in
                        ("cluster", "instance_id", "branch_id", "tenant_id")) for record in logs}
    direct = {(record["time_unix_nano"], record.get("line", "")) for record in logs}
    candidates = {}
    for cluster, instance in sorted({item[:2] for item in identities}):
        if not cluster or not instance:
            continue
        branches = {item[2] for item in identities if item[:2] == (cluster, instance) and item[2]}
        tenants = {item[3] for item in identities if item[:2] == (cluster, instance) and item[3]}
        for record in search_logs(client, env, "instance_id", instance, start, end, gaps, cluster=cluster):
            fields = record["fields"]
            if (fields.get("cluster") != cluster or fields.get("instance_id") != instance
                    or branches and fields.get("branch_id") not in branches
                    or tenants and fields.get("tenant_id") not in tenants):
                continue
            key = (record["time_unix_nano"], record.get("line", ""))
            level = str(fields.get("level", record.get("stream", {}).get("detected_level", ""))).lower()
            if key not in direct and (level in {"error", "fatal"} or failure_evidence([record])["failure_events"]):
                candidates[key] = record
    return sorted(candidates.values(), key=lambda record: int(record["time_unix_nano"]))


def canonical_trace_id(value: str) -> str:
    return value.lower().zfill(32) if TRACE_ID.fullmatch(value) else value


def tempo_window(client: Backend, field: str, value: str, start: int, end: int,
                 traces: dict, gaps: list[str], component: str = "",
                 cluster: str = "", environment: str = "") -> None:
    parts = ["span." + field + " = " + json.dumps(value)]
    if environment:
        parts.append("resource.deployment.environment.name = " + json.dumps(environment))
    if component:
        parts.append("resource.service.name = " + json.dumps(component))
    if cluster:
        parts.append("span.tiana.cluster = " + json.dumps(cluster))
    query = "{ " + " && ".join(parts) + " }"
    response = client.get("tempo", "/api/search", {
        "q": query, "start": str(start), "end": str(end), "limit": str(TRACE_LIMIT),
    })
    page = response.get("traces", [])
    for trace in page:
        trace_id = trace.get("traceID")
        if trace_id:
            traces[canonical_trace_id(trace_id)] = trace
    if len(page) < TRACE_LIMIT:
        return
    if end - start <= 1:
        gaps.append(f"Tempo saturated at second {start}; further traces may be missing")
        return
    middle = (start + end) // 2
    tempo_window(client, field, value, start, middle, traces, gaps, component, cluster, environment)
    tempo_window(client, field, value, middle, end, traces, gaps, component, cluster, environment)


def search_traces(client: Backend, field: str, value: str, start: datetime,
                  end: datetime, gaps: list[str], component: str = "",
                  cluster: str = "", environment: str = "") -> dict:
    traces: dict = {}
    for left, right in bounded_windows(start, end):
        try:
            tempo_window(client, field, value, math.floor(left.timestamp()),
                         math.ceil(right.timestamp()), traces, gaps, component, cluster, environment)
        except QueryError as exc:
            gaps.append(str(exc))
    return traces


def fetch_traces(client: Backend, ids: set[str], gaps: list[str]) -> dict:
    results = {}
    for trace_id in sorted(ids):
        if not TRACE_ID.fullmatch(trace_id):
            gaps.append(f"Ignored invalid trace ID in result: {trace_id}")
            continue
        try:
            # A time bound can omit part of a trace, so exact ID lookup is unbounded.
            results[trace_id] = client.get("tempo", "/api/traces/" + quote(trace_id))
        except QueryError as exc:
            gaps.append(str(exc))
    return results


def task_ids(logs: list[dict]) -> set[tuple[str, str, str, str]]:
    found = set()
    for record in logs:
        fields = record["fields"]
        for key in ("job_id", "operation_id", "collaboration_id", "transaction_id", "expiry_plan_id"):
            if fields.get(key):
                found.add((key, str(fields[key]), str(fields.get("component", "")),
                           str(fields.get("cluster", ""))))
        for key in ("target_job_id", "target_operation_id", "dependency_job_id", "parent_job_id"):
            if fields.get(key):
                kind = "operation_id" if key.endswith("operation_id") else "job_id"
                found.add((kind, str(fields[key]),
                           str(fields.get("target_component", fields.get("component", ""))),
                           str(fields.get("target_cluster", fields.get("cluster", "")))))
    return found



def async_acceptance_gaps(logs: list[dict], gaps: list[str]) -> None:
    linked_requests, linked_traces = set(), set()
    for record in logs:
        if not task_ids([record]):
            continue
        fields = record["fields"]
        if fields.get("request_id"):
            linked_requests.add(str(fields["request_id"]))
        if fields.get("trace_id"):
            linked_traces.add(str(fields["trace_id"]))
    for record in logs:
        fields = record["fields"]
        if (fields.get("component") != "mgr" or fields.get("event") != "request.completed"
                or str(fields.get("status")) != "202"):
            continue
        request_id, trace_id = str(fields.get("request_id", "")), str(fields.get("trace_id", ""))
        if request_id not in linked_requests and trace_id not in linked_traces:
            gap = f"MGR accepted HTTP 202 request={request_id or '-'} trace={trace_id or '-'} but no associated task identity was found; asynchronous evidence is incomplete"
            if gap not in gaps:
                gaps.append(gap)


def failure_evidence(logs: list[dict], request_id: str = "") -> dict:
    observed = []
    for record in logs:
        fields = record["fields"]
        app_status = fields.get("app_http_status")
        if isinstance(app_status, str) and app_status.isdecimal():
            app_status = int(app_status)
        if isinstance(app_status, int) and app_status >= 400:
            observed.append({"time_unix_nano": record["time_unix_nano"],
                             "component": "app", "event": fields.get("event", ""),
                             "reason": f"App returned HTTP {app_status}",
                             "kind": "app_response", "http_status": app_status,
                             "trace_id": fields.get("trace_id", ""),
                             "request_id": fields.get("request_id", "")})
        status = fields.get("status")
        if isinstance(status, str) and status.isdecimal():
            status = int(status)
        failed = (str(fields.get("outcome", "")).lower() in {"failed", "error"}
                  or (fields.get("outcome") == "retry" and bool(fields.get("reason_code")))
                  or str(fields.get("event", "")).endswith((".failed", ".error", ".rejected"))
                  or str(fields.get("level", "")).lower() in {"error", "fatal"}
                  or isinstance(status, int) and status >= 400)
        if not failed:
            continue
        reason = next((str(fields[key]) for key in
                       ("error_kind", "error_code", "reason_code", "error", "reason", "last_error")
                       if fields.get(key)), "")
        observed.append({"time_unix_nano": record["time_unix_nano"],
                         "component": fields.get("component", record["stream"].get("component", "")),
                         "event": fields.get("event", ""), "reason": reason,
                         "direction": str(fields.get("direction", "")),
                         "stage": str(fields.get("stage", "")),
                         "dependency": str(fields.get("dependency", "")),
                         "target_component": str(fields.get("target_component", "")),
                         "target_cluster": str(fields.get("target_cluster", "")),
                         "target_operation_id": str(fields.get("target_operation_id", "")),
                         "server_address": str(fields.get("server_address", "")),
                         "path": str(fields.get("path", "")),
                         "http_status": status if isinstance(status, int) else None,
                         "detail": str(fields.get("reason", "")) if fields.get("reason") != reason else "",
                         "job_id": str(fields.get("job_id", "")),
                         "operation_id": str(fields.get("operation_id", "")),
                         "cluster": str(fields.get("cluster", "")),
                         "trace_id": fields.get("trace_id", ""),
                         "request_id": fields.get("request_id", "")})
    direct_events = [event for event in observed
                     if event["component"] and event["reason"]
                     and event.get("kind") != "app_response"
                     and not (event["component"] == "gateway" and event["event"] == "connection.closed")
                     and not (event["component"] == "control"
                              and event["event"].startswith("task.")
                              and (event["reason"] == "STORE_DELETE_UNCONFIRMED"
                                   or event["reason"].startswith("STORE_DELETE_UNCONFIRMED:")))
                     and not (event["component"] == "mgr"
                              and event["event"].startswith("task.")
                              and event["reason"] == "SYNC_UNAVAILABLE")
                     and not (event["component"] == "gateway"
                              and (event["event"], event["reason"]) in {
                                  ("gateway.connect.failed", "PolicyCache"),
                                  ("gateway.connect.failed", "Ensure(ActivationDeadline)"),
                                  ("gateway.connect.failed", "Handshake(NotOk(AppUnavailable))"),
                                  ("request.rejected", "INSTANCE_UNAVAILABLE"),
                              })]
    direct = next((event for event in direct_events if request_id and event["request_id"] == request_id),
                  next(iter(direct_events), None))
    if direct and direct["event"] == "http.client.failed" and direct["trace_id"] and not direct["job_id"]:
        attempt_jobs = {str(record["fields"]["job_id"]) for record in logs
                        if record["fields"].get("event") == "task.attempt.finished"
                        and record["fields"].get("component") == direct["component"]
                        and record["fields"].get("trace_id") == direct["trace_id"]
                        and record["fields"].get("job_id")}
        if len(attempt_jobs) == 1:
            direct["job_id"] = next(iter(attempt_jobs))
    first = observed[0] if observed else None
    component = (direct or first or {}).get("component", "")
    if (direct and direct["event"] == "http.client.failed"
            and direct["reason"] == "downstream_http_error"
            and direct["path"].startswith("/control/")
            and isinstance(direct["http_status"], int) and direct["http_status"] >= 500):
        component = "control"
    if (direct and direct["event"] == "task.target.failed"
            and direct["target_component"] == "control"):
        component = "control"
    if direct is None and first and first["component"] == "gateway" and first["event"] == "connection.closed":
        component = ""
    return {"failure_component": component,
            "root_cause_evidence": direct,
            "candidate_failure": first if direct is None else None,
            "failure_events": observed}


def trace_span_rows(traces: dict) -> list[dict]:
    rows = []
    for trace_id, document in traces.items():
        for batch in document.get("batches", []):
            resource = {item.get("key"): item.get("value", {}).get("stringValue", "")
                        for item in batch.get("resource", {}).get("attributes", [])}
            service = resource.get("service.name", "unknown")
            for scope in batch.get("scopeSpans", batch.get("instrumentationLibrarySpans", [])):
                for span in scope.get("spans", []):
                    attributes = {item.get("key"): next(iter(item.get("value", {}).values()), "")
                                  for item in span.get("attributes", [])}
                    started = int(span.get("startTimeUnixNano", 0))
                    ended = int(span.get("endTimeUnixNano", started))
                    rows.append({"time_unix_nano": started, "trace_id": trace_id,
                                 "component": service, "name": span.get("name", ""),
                                 "span_id": span.get("spanId", ""),
                                 "parent_span_id": span.get("parentSpanId", ""),
                                 "http_status": attributes.get("http.response.status_code", ""),
                                 "error_type": attributes.get("error.type", ""),
                                 "reason": attributes.get("reason_code", span.get("status", {}).get("message", "")),
                                 "duration_ms": max(0, ended - started) / 1e6,
                                 "request_id": attributes.get("tiana.request.id", attributes.get("request_id", "")),
                                 "operation_id": str(attributes.get("tiana.operation.id", "")),
                                 "job_id": str(attributes.get("tiana.job.id", "")),
                                 "tenant_id": attributes.get("tiana.tenant.id", ""),
                                 "instance_id": attributes.get("tiana.instance.id", ""),
                                 "branch_id": attributes.get("tiana.branch.id", ""),
                                 "cluster": attributes.get("tiana.cluster", resource.get("tiana.cluster", "")),
                                 "status": span.get("status", {}).get("code", 0)})
    return sorted(rows, key=lambda row: row["time_unix_nano"])


def connection_trace_gaps(traces: dict, gaps: list[str], logs: list[dict] = ()) -> None:
    connection_traces = {record["fields"].get("trace_id") for record in logs
                         if record["fields"].get("component") in ("gateway", "agent")
                         and record["fields"].get("event") == "connection.closed"}
    for trace_id, document in traces.items():
        spans = trace_span_rows({trace_id: document})
        names = {(span["component"], span["name"]) for span in spans}
        if ((trace_id in connection_traces or ("tiana-agent", "agent.session.establish_route") in names)
                and ("tiana-gateway", "gateway.session.establish") not in names
                and ("tiana-gateway", "gateway.fetch") not in names):
            gaps.append(f"Connection Trace {trace_id} has connection evidence but is missing the Gateway ingress span")


def add_span_findings(diagnosis: dict, traces: dict) -> None:
    failures = [span for span in trace_span_rows(traces)
                if span["status"] in (2, "STATUS_CODE_ERROR")]
    diagnosis["span_failures"] = failures
    if failures and not diagnosis["failure_component"]:
        first = failures[0]
        diagnosis["failure_component"] = first["component"]
        diagnosis["candidate_failure"] = {"kind": "span", "component": first["component"],
                                          "trace_id": first["trace_id"], "span_id": first["span_id"],
                                          "reason": first["reason"]}


def output_dir(args: argparse.Namespace, label: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", label)
    root = Path(args.output or f"tiana-debug-{safe}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}")
    root.mkdir(parents=True, exist_ok=True)
    return root


def recovered_attempt(finding: dict, tasks: list[dict]) -> bool:
    event, state = (("task.attempt.completed", "succeeded")
                    if finding.get("component") == "gaia"
                    else ("task.attempt.finished", "success"))
    outbound_attempt = (finding.get("event") == "http.client.failed"
                        and bool(finding.get("trace_id")) and bool(finding.get("job_id")))
    if finding.get("event") != event and not outbound_attempt:
        return False
    return any(task["state"] == state
               and finding.get(task["kind"]) == task["identity"]
               and finding.get("component") == task["component"]
               and (outbound_attempt or finding.get("cluster", "") == task["cluster"])
               for task in tasks)


def recovered_task_span(span: dict, tasks: list[dict]) -> bool:
    component = span.get("component", "").removeprefix("tiana-")
    event = "task.attempt.completed" if component == "gaia" else "task.attempt.finished"
    return recovered_attempt(dict(span, component=component, event=event), tasks)


def evidence_files(root: Path, summary: dict, logs: list[dict], traces: dict,
                   gaia_operations: list[dict] | None = None,
                   gaia_events: dict[str, list[dict]] | None = None) -> None:
    spans = trace_span_rows(traces)
    summary["timeline_display_truncated"] = max(0, len(logs) + len(spans) - 300)
    (root / "evidence.json").write_text(json_text(summary) + "\n", encoding="utf-8")
    with (root / "logs.jsonl").open("w", encoding="utf-8") as handle:
        for record in logs:
            handle.write(json_text(record, indent=None) + "\n")
    with (root / "resource-candidates.jsonl").open("w", encoding="utf-8") as handle:
        for record in summary.get("resource_candidates", []):
            handle.write(json_text(record, indent=None) + "\n")
    trace_dir = root / "traces"
    trace_dir.mkdir(exist_ok=True)
    for trace_id, document in traces.items():
        (trace_dir / f"{trace_id}.json").write_text(json_text(document) + "\n", encoding="utf-8")
    if gaia_operations is not None:
        (root / "gaia_operations.json").write_text(json_text(gaia_operations) + "\n", encoding="utf-8")
    if gaia_events is not None:
        (root / "gaia_events.json").write_text(json_text(gaia_events) + "\n", encoding="utf-8")
    report = ["# Tiana diagnosis", "", f"Environment: {summary['environment']}",
              f"Identity: {summary['identity']}", f"Status: {summary['status']}",
              f"Window: {summary['window']['start']} to {summary['window']['end']}",
              f"Logs: {len(logs)}; full traces: {len(traces)}", ""]
    diagnosis = summary["diagnosis"]
    component = diagnosis["failure_component"] or (
        "none observed" if diagnosis.get("terminal_state") == "success" else "undetermined")
    report += ["## Failure finding", "", f"Component: {component}"]
    if recovered_attempt(diagnosis.get("root_cause_evidence") or {}, diagnosis.get("task_terminal_states", [])):
        report.append("The associated task succeeded after retry; the following attempt error is historical.")
    for operation in gaia_operations or []:
        report.append(f"Gaia Operation {operation.get('operation_id', '-')}: {operation.get('state', 'unknown')} at {operation.get('step', '-')}; error: {operation.get('error_code', '-')}")
    for control in diagnosis.get("control_requests", []):
        report.append(f"Gaia control {control.get('request_id', '-')} ({control.get('action', '-')}): {control.get('state', 'unknown')}; result: {control.get('result_code', '')} {control.get('result_message', '')}")
    if diagnosis.get("terminal_state") and not diagnosis.get("task_terminal_states"):
        report.append(f"Operation terminal state: {diagnosis['terminal_state']}")
    for task in diagnosis.get("task_terminal_states", []):
        report.append(f"Task {task['kind']}={task['identity']} ({task['component']}, {task['cluster']}): {task['state']}")
    if diagnosis["root_cause_evidence"]:
        finding = diagnosis["root_cause_evidence"]
        prefix = "Recovered attempt failure" if recovered_attempt(finding, diagnosis.get("task_terminal_states", [])) else "Direct failure event"
        report.append(f"{prefix}: {finding['event'] or '-'}; reason: {finding['reason']}; trace: {finding['trace_id'] or '-'}")
        if finding.get("target_component"):
            report.append(f"Target: {finding['target_component']} cluster={finding.get('target_cluster') or finding.get('cluster') or '-'} operation={finding.get('target_operation_id') or '-'}")
        if finding.get("detail"):
            report.append(f"Observed detail: {finding['detail']}")
        if finding.get("dependency") or finding.get("server_address"):
            report.append(f"Observed downstream target: {finding.get('dependency') or finding.get('server_address')}; path: {finding.get('path') or '-'}")
    elif diagnosis["candidate_failure"]:
        if diagnosis["candidate_failure"].get("kind") == "span":
            report.append("A failed Span was observed; the underlying cause is not established by a correlated failure log.")
        elif diagnosis["candidate_failure"].get("kind") == "app_response":
            report.append(f"App returned HTTP {diagnosis['candidate_failure']['http_status']}; inspect the App Trace and logs for the underlying cause.")
        elif (diagnosis["candidate_failure"].get("component") == "gateway"
              and diagnosis["candidate_failure"].get("event") == "connection.closed"):
            report.append("Gateway observed a transport close; this alone does not establish a failed SQL or Git operation or identify its cause. Compare the client result with the Trace and adjacent logs.")
        else:
            report.append("Candidate failure event without a structured reason; inspect its Trace and adjacent logs.")
    else:
        report.append("No structured failure event was found in the collected logs.")
    for span in diagnosis.get("span_failures", [])[:20]:
        prefix = "Recovered task attempt Span" if recovered_task_span(span, diagnosis.get("task_terminal_states", [])) else "Failed Span"
        report.append(f"{prefix}: {span['component']} {span['name']}; HTTP={span['http_status'] or '-'}; "
                      f"reason={span['reason'] or span['error_type'] or '-'}; trace={span['trace_id']}; span={span['span_id']}")
    if len(diagnosis.get("span_failures", [])) > 20:
        report.append("Additional failed Spans are recorded in evidence.json.")
    report.append("")
    candidates = summary.get("resource_candidates", [])
    if candidates:
        report.extend(["## Resource and time candidates", "",
                       "These errors match a known resource and the selected time window; causation is unproven.",
                       f"Records: {len(candidates)}; full evidence: resource-candidates.jsonl", ""])
        for record in candidates[:10]:
            report.append(f"- {record['time_unix_nano']}: {record.get('line', '')}")
        if len(candidates) > 10:
            report.append(f"Display truncated: {len(candidates) - 10} additional candidates are in the evidence file.")
        report.append("")
    if gaia_events:
        report += ["## Gaia stages", ""]
        for operation_id, events in gaia_events.items():
            for event in events:
                report.append(f"- {event.get('created_at', '-')} {operation_id} {event.get('step', '-')}: {event.get('message', '-')}")
        report.append("")
    if summary["gaps"]:
        report += ["## Evidence gaps", ""] + [f"- {clean(gap)}" for gap in summary["gaps"]] + [""]
    report += ["## Timeline", ""]
    timeline = []
    for record in logs:
        fields = record["fields"]
        timeline.append((int(record["time_unix_nano"]),
                         f"log {fields.get('component', record['stream'].get('component', '?'))}: "
                         f"{fields.get('event', clean(record['line'])[:180])} "
                         f"trace={fields.get('trace_id', '-')} "
                         f"tenant={fields.get('tenant_id', '-')} "
                         f"instance={fields.get('instance_id', '-')} "
                         f"branch={fields.get('branch_id', '-')} "
                         f"cluster={fields.get('cluster', '-')}"))
    for span in spans:
        timeline.append((span["time_unix_nano"],
                         f"span {span['component']}: {span['name']} "
                         f"duration_ms={span['duration_ms']:.3f} status={span['status']} HTTP={span['http_status'] or '-'} "
                         f"trace={span['trace_id']} request={span['request_id'] or '-'} "
                         f"tenant={span['tenant_id'] or '-'} instance={span['instance_id'] or '-'} "
                         f"branch={span['branch_id'] or '-'} cluster={span['cluster'] or '-'}"))
    timeline.sort(key=lambda item: item[0])
    for started, item in timeline[:300]:
        when = datetime.fromtimestamp(started / 1e9, UTC).isoformat()
        report.append(f"- {when} {item}")
    if len(timeline) > 300:
        report.append(f"- Timeline display truncated: {len(timeline) - 300} additional events; complete logs and traces are in the evidence files.")
    report += ["", "## Interpretation", "",
               "Use direct failure events and the full Trace to determine the failing component. "
               "Time and resource matches alone are candidates.", ""]
    (root / "diagnosis.md").write_text(clean("\n".join(report)), encoding="utf-8")


def selected_window(args: argparse.Namespace, profile: dict) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    end = instant(args.until) if args.until else now
    start = instant(args.since) if args.since else end - DAY
    floor = now - timedelta(hours=int(profile.get("retention_hours", 168)))
    if start >= end:
        raise QueryError("Selected start must precede the end of the query window")
    if end <= floor:
        raise RetentionWindowUnavailable(start, end)
    return max(start, floor), end


def connection_window_start(logs: list[dict], start: datetime, floor: datetime,
                            gaps: list[str]) -> datetime:
    earliest = start
    for record in logs:
        fields = record["fields"]
        if fields.get("event") != "connection.closed" or "duration_ms" not in fields:
            continue
        try:
            opened_ns = int(record["time_unix_nano"]) - int(fields["duration_ms"]) * 1_000_000
            opened = datetime.fromtimestamp(opened_ns / 1e9, UTC)
        except (ValueError, TypeError, OverflowError, OSError):
            gaps.append("Connection close has an unreadable start time; establishment lookup is incomplete")
            continue
        if opened < floor:
            gap = "Connection began before the available retention window; establishment evidence outside that window cannot be queried"
            if gap not in gaps:
                gaps.append(gap)
        earliest = min(earliest, max(opened - timedelta(seconds=1), floor))
    return earliest


def investigate(args: argparse.Namespace, profile: dict, client: Backend) -> int:
    if not IDENTIFIER.fullmatch(args.identity):
        raise QueryError("Identity contains unsupported characters")
    gaps: list[str] = []
    try:
        start, end = selected_window(args, profile)
    except RetentionWindowUnavailable as exc:
        root = output_dir(args, args.identity)
        summary = {"environment": args.env, "identity": args.identity, "status": "partial",
                   "window": {"start": exc.start.isoformat(), "end": exc.end.isoformat()},
                   "trace_ids": [], "task_ids": [], "diagnosis": failure_evidence([]),
                   "gaps": [str(exc)], "queries": client.queries}
        evidence_files(root, summary, [], {})
        print(f"partial: {root / 'diagnosis.md'}")
        return 2
    retention_floor = datetime.now(UTC) - timedelta(hours=int(profile.get("retention_hours", 168)))
    if args.since and instant(args.since) < retention_floor:
        gaps.append("Requested start precedes available retention; the query window was clipped")
    if args.command == "request":
        field = "request_id"
    else:
        field = "job_id" if args.component == "mgr" else "operation_id"
    component = args.component if args.command == "operation" else ""
    cluster = args.cluster if args.command == "operation" else ""
    logs = search_logs(client, args.env, field, args.identity, start, end, gaps,
                       component, cluster)
    search_field = {"request_id": "tiana.request.id", "job_id": "job_id", "operation_id": "tiana.operation.id"}[field]
    trace_hits = search_traces(client, search_field, args.identity, start, end, gaps,
                               component, cluster, args.env)
    if not args.since and not args.until and not logs and not trace_hits:
        earlier = max(datetime.now(UTC) - timedelta(hours=int(profile.get("retention_hours", 168))),
                      start - timedelta(days=6))
        logs = search_logs(client, args.env, field, args.identity, earlier, start, gaps,
                           component, cluster)
        trace_hits = search_traces(client, search_field, args.identity, earlier, start,
                                   gaps, component, cluster, args.env)
        start = earlier
    expanded_start = connection_window_start(logs, start, retention_floor, gaps)
    if expanded_start < start:
        logs.extend(search_logs(client, args.env, field, args.identity, expanded_start, start,
                                gaps, component, cluster))
        trace_hits.update(search_traces(client, search_field, args.identity, expanded_start, start,
                                       gaps, component, cluster, args.env))
        start = expanded_start
    seen = {(field, args.identity, component, cluster)}
    if args.command == "operation":
        seen.remove((field, args.identity, component, cluster))
    traces: dict = {}
    queried_traces: set[str] = set()
    while True:
        pending_tasks = sorted(task_ids(logs) - seen)
        if args.command == "operation" and (field, args.identity, component, cluster) not in seen:
            pending_tasks.insert(0, (field, args.identity, component, cluster))
        ids = {canonical_trace_id(value) for value in trace_hits}
        ids.update(canonical_trace_id(str(log["fields"]["trace_id"])) for log in logs if log["fields"].get("trace_id"))
        pending_traces = ids - queried_traces
        if not pending_tasks and not pending_traces:
            break
        for kind, identity, owner, home in pending_tasks:
            key = (kind, identity, owner, home)
            if key in seen:
                continue
            seen.add(key)
            if not owner or (owner == "control" and not home):
                gaps.append(f"Task {kind}={identity} lacks its owning component or Control cluster; task expansion is incomplete")
                continue
            logs.extend(search_logs(client, args.env, kind, identity, start, end, gaps, owner, home))
        if pending_traces:
            queried_traces.update(pending_traces)
            found = fetch_traces(client, pending_traces, gaps)
            traces.update(found)
            for trace_id in found:
                logs.extend(search_logs(client, args.env, "trace_id", trace_id, start, end, gaps))
    unique_logs = {(record["time_unix_nano"], json.dumps(record["stream"], sort_keys=True), record["line"]): record for record in logs}
    logs = sorted(unique_logs.values(), key=lambda event: int(event["time_unix_nano"]))
    gaia_operations = []
    gaia_controls = []
    gaia_events = {}
    gaia_ids = {identity for kind, identity, owner, _ in seen
                if kind == "operation_id" and owner == "gaia"}
    for identity in sorted(gaia_ids):
        try:
            path = "/api/v1/platform/deployment-operations/" + quote(identity, safe="")
            result = client.get("gaia", path)
            if not isinstance(result, dict):
                raise QueryError(f"Gaia Operation {identity} returned no object")
            gaia_operations.append(result)
            control_ids = {str(record["fields"]["control_request_id"]) for record in logs
                           if record["fields"].get("component") == "gaia"
                           and record["fields"].get("operation_id") == identity
                           and record["fields"].get("control_request_id")
                           and (args.command != "request" or record["fields"].get("request_id") == args.identity)}
            if control_ids:
                try:
                    controls = client.get("gaia", path + "/controls")
                    if not isinstance(controls, dict) or not isinstance(controls.get("items"), list):
                        raise QueryError(f"Gaia Operation {identity} control requests are missing")
                    matched = [item for item in controls["items"] if item.get("request_id") in control_ids]
                    gaia_controls.extend(matched)
                    missing = control_ids - {item["request_id"] for item in matched}
                    if missing:
                        gaps.append(f"Gaia Operation {identity} control requests not found: {', '.join(sorted(missing))}")
                except QueryError as exc:
                    gaps.append(str(exc))
            gaia_events[identity] = []
            after = 0
            while True:
                events = client.get("gaia", path + "/events", {"after": after})
                if not isinstance(events, dict) or not isinstance(events.get("items"), list):
                    raise QueryError(f"Gaia Operation {identity} events are missing")
                items = events["items"]
                gaia_events[identity].extend(items)
                if len(items) < 200:
                    break
                cursor = items[-1].get("sequence", 0)
                if not isinstance(cursor, int) or cursor <= after:
                    raise QueryError(f"Gaia Operation {identity} event cursor did not advance; evidence truncated")
                after = cursor
        except QueryError as exc:
            gaps.append(str(exc))
    connection_trace_gaps(traces, gaps, logs)
    async_acceptance_gaps(logs, gaps)
    if not logs:
        gaps.append("No matching Loki records in the selected window")
    if not traces:
        gaps.append("No matching Tempo traces in the selected window")
    for record in logs:
        fields = record["fields"]
        if fields.get("diagnostic_reason") == "operation_result_unavailable":
            gaps.append(f"Control operation result unavailable: cluster={fields.get('cluster', '-')} operation={fields.get('operation_id', '-')}")
        if fields.get("event") == "telemetry.context.missing":
            gaps.append(f"Diagnostic linkage missing in {fields.get('component', '?')}: "
                        f"{fields.get('reason_code', 'unknown')} "
                        f"request={fields.get('request_id', '-')} ticket={fields.get('ticket_id', '-')}")
    status = "partial" if gaps else "complete"
    root = output_dir(args, args.identity)
    diagnosis = failure_evidence(logs, args.identity if args.command == "request" else "")
    add_span_findings(diagnosis, traces)
    candidates = resource_failure_candidates(client, args.env, logs, start, end, gaps)
    status = "partial" if gaps else "complete"
    task_states = []
    for kind, identity, owner, home in sorted(seen):
        if kind == "transaction_id" and owner == "mgr":
            terminal_phases = {"auth.transaction.denied": "denied",
                               "auth.transaction.expired": "expired",
                               "auth.token.issued": "completed"}
            terminal = [record for record in logs
                        if str(record["fields"].get("transaction_id", "")) == identity
                        and record["fields"].get("component") == owner
                        and record["fields"].get("event") == "auth.transaction.link"
                        and record["fields"].get("phase") in terminal_phases]
            if terminal:
                fields = terminal[-1]["fields"]
                task_states.append({"kind": kind, "identity": identity, "component": owner,
                                    "cluster": home, "state": terminal_phases[fields["phase"]],
                                    "event": fields["phase"], "request_id": fields.get("request_id", ""),
                                    "trace_id": fields.get("trace_id", "")})
            continue
        if kind not in {"job_id", "operation_id"}:
            continue
        completed = [record for record in logs if
                     str(record["fields"].get(kind, "")) == identity and
                     str(record["fields"].get("component", "")) == owner and
                     str(record["fields"].get("cluster", "")) == home and
                     record["fields"].get("event") == "task.completed"]
        if completed:
            task_states.append({"kind": kind, "identity": identity, "component": owner,
                                "cluster": home,
                                "state": str(completed[-1]["fields"].get("outcome", "unknown"))})
    if task_states:
        diagnosis["task_terminal_states"] = task_states
        if len(task_states) == 1:
            diagnosis["terminal_state"] = task_states[0]["state"]
    for gaia_operation in gaia_operations:
        if gaia_operation.get("state") != "FAILED":
            continue
        failed_step = gaia_operation.get("step", "")
        if not diagnosis.get("root_cause_evidence"):
            diagnosis["failure_component"] = {"sync_mgr": "mgr", "apply_data_node_monitoring": "data-node-monitoring", "verify_observability": "observability"}.get(failed_step, "gaia")
            diagnosis["root_cause_evidence"] = {
                "event": "operation.failed", "reason": gaia_operation.get("error_message") or gaia_operation.get("error_code", ""),
                "trace_id": "", "operation_id": gaia_operation.get("operation_id", ""), "step": failed_step}
    if gaia_controls:
        diagnosis["control_requests"] = gaia_controls
        rejected = [item for item in gaia_controls if item.get("state") == "REJECTED"]
        if rejected:
            item = rejected[-1]
            diagnosis["failure_component"] = "gaia"
            if not diagnosis.get("root_cause_evidence"):
                diagnosis["root_cause_evidence"] = {
                    "event": "operation.control.rejected", "reason": item.get("result_code", ""),
                    "detail": item.get("result_message", ""), "trace_id": "",
                    "operation_id": item.get("operation_id", ""), "control_request_id": item.get("request_id", "")}
    summary = {"environment": args.env, "identity": args.identity,
               "status": status, "window": {"start": start.isoformat(), "end": end.isoformat()},
               "trace_ids": sorted(traces), "task_ids": sorted([list(item) for item in seen if item[0] in {"job_id", "operation_id", "collaboration_id", "transaction_id", "expiry_plan_id"}]),
               "diagnosis": diagnosis, "resource_candidates": candidates, "gaia_operations": gaia_operations,
               "gaps": gaps, "queries": client.queries}
    evidence_files(root, summary, logs, traces, gaia_operations, gaia_events)
    print(f"{status}: {root / 'diagnosis.md'}")
    return 0 if status == "complete" else 2


def doctor(args: argparse.Namespace, profile: dict, client: Backend) -> int:
    checks = {}
    calls = (("loki", "/loki/api/v1/labels", {}),
             ("tempo", "/ready", {}),
             ("prometheus", "/api/v1/targets", {}))
    for name, path, params in calls:
        try:
            client.get(name, path, params)
            checks[name] = "available"
        except QueryError as exc:
            checks[name] = str(exc)
    if profile.get("gaia_origin"):
        try:
            client.get("gaia", "/deployment-readyz")
            checks["gaia"] = "available"
        except QueryError as exc:
            checks["gaia"] = str(exc)
    checks["retention_hours"] = profile.get("retention_hours", 168)
    print(json_text(checks))
    return 0 if all(value == "available" for key, value in checks.items() if key != "retention_hours") else 2


def metric_coverage(series: list[dict], end_timestamp: float) -> str:
    if not series:
        return "missing"
    fresh = [item for item in series if item.get("values") and
             end_timestamp - float(item["values"][-1][0]) <= 120]
    if not fresh:
        return "stale"
    finite = 0
    for item in fresh:
        try:
            finite += math.isfinite(float(item["values"][-1][1]))
        except (ValueError, TypeError, IndexError):
            pass
    if not finite:
        return "no_samples"
    return "data" if finite == len(series) else "partial"


def scrape_target_coverage(series: list[dict], targets: list[dict], end_timestamp: float,
                           environment: str, cluster: str | None) -> str:
    current = {frozenset(target["labels"].items()) for target in targets
               if target.get("labels", {}).get("environment") == environment
               and (not cluster or target["labels"].get("cluster") == cluster)}
    selected = [item for item in series
                if frozenset((key, value) for key, value in item.get("metric", {}).items()
                             if key != "__name__") in current]
    state = metric_coverage(selected, end_timestamp)
    return "partial" if state == "data" and len(selected) < len(current) else state


def inspect(args: argparse.Namespace, profile: dict, client: Backend) -> int:
    end = datetime.now(UTC)
    try:
        hours = int(args.window.removesuffix("h"))
    except ValueError as exc:
        raise QueryError("--window must be a number of hours, such as 24h") from exc
    if hours <= 0 or hours > int(profile.get("retention_hours", 168)):
        raise QueryError("--window is outside the available retention range")
    start = end - timedelta(hours=hours)
    selector = "environment=" + json.dumps(args.env)
    if args.cluster:
        selector += ",cluster=~" + json.dumps("(" + re.escape(args.cluster) + ")?")
    promql = {
        "ingress_rate": f"sum by(component)(rate(tiana_http_requests_total{{{selector}}}[5m]))",
        "ingress_failures": f"sum by(component)(rate(tiana_http_requests_total{{{selector},outcome=\"failed\"}}[5m])) or on(component) (0 * sum by(component)(rate(tiana_http_requests_total{{{selector}}}[5m])))",
        "connect_p99": f"histogram_quantile(0.99,sum by(le)(rate(tiana_gateway_connect_to_first_upstream_byte_seconds_bucket{{{selector}}}[5m])))",
        "parked_agents": f"sum by(cluster)(tiana_runtime_agents_parked{{{selector}}})",
        "configured_agents": f"sum by(cluster)(tiana_runtime_agents_configured{{{selector}}})",
        "failed_agents": f"sum by(cluster,node_id)(tiana_runtime_agents_failed{{{selector}}})",
        "failed_tasks": f"sum by(component)(rate(tiana_task_completions_total{{{selector},outcome=\"failed\"}}[5m])) or on(component) (0 * sum by(component)(rate(tiana_task_completions_total{{{selector}}}[5m])))",
        "runtime_heartbeat_age": f"max by(node_id)(time() - tiana_runtime_state_stream_last_heartbeat_unixtime{{{selector}}})",
        "node_cpu_busy": f"1 - avg by(node_id)(rate(node_cpu_seconds_total{{{selector},mode=\"idle\"}}[5m]))",
        "node_disk_available": f"min by(node_id)(node_filesystem_avail_bytes{{{selector},fstype!~\"tmpfs|overlay\"}})",
        "collector_refused_logs": f"sum by(component)(rate(otelcol_receiver_refused_log_records{{{selector}}}[5m]))",
        "collector_refused_spans": f"sum by(component)(rate(otelcol_receiver_refused_spans{{{selector}}}[5m]))",
        "collector_enqueue_failed_logs": f"sum by(component,exporter)(rate(otelcol_exporter_enqueue_failed_log_records{{{selector}}}[5m]))",
        "collector_enqueue_failed_spans": f"sum by(component,exporter)(rate(otelcol_exporter_enqueue_failed_spans{{{selector}}}[5m]))",
        "collector_queue_usage": f"otelcol_exporter_queue_size{{{selector}}} / otelcol_exporter_queue_capacity{{{selector}}}",
        "collector_accepted_logs": f"sum by(component)(rate(otelcol_receiver_accepted_log_records{{{selector}}}[5m]))",
        "node_memory_available_ratio": f"node_memory_MemAvailable_bytes{{{selector}}} / node_memory_MemTotal_bytes{{{selector}}}",
        "collector_export_failed_logs": f"sum by(component,exporter)(rate(otelcol_exporter_send_failed_log_records{{{selector}}}[5m]))",
        "collector_export_failed_spans": f"sum by(component,exporter)(rate(otelcol_exporter_send_failed_spans{{{selector}}}[5m]))",
        "scrape_up": f"up{{{selector}}}",
    }
    for kind in ("COLD", "HOT"):
        for quantile in (0.5, 0.95, 0.99):
            name = f"establish_{kind.lower()}_p{int(quantile * 100)}"
            promql[name] = f'histogram_quantile({quantile},sum by(le,transport,protocol)(rate(tiana_gateway_establish_duration_seconds_bucket{{{selector},activation_kind="{kind}",outcome="success"}}[5m])))'
    for phase in ("response_start", "completion"):
        promql[f"fetch_{phase}_p99"] = f'histogram_quantile(0.99,sum by(le,activation_kind,transport,protocol)(rate(tiana_gateway_fetch_duration_seconds_bucket{{{selector},phase="{phase}",outcome="success"}}[5m])))'
    promql["gateway_stage_p95"] = f'histogram_quantile(0.95,sum by(le,stage)(rate(tiana_gateway_stage_duration_seconds_bucket{{{selector},outcome="success"}}[5m])))'
    results: dict = {"environment": args.env, "cluster": args.cluster,
                     "scope": "shared platform and selected cluster" if args.cluster else "environment",
                     "window": {"start": start.isoformat(), "end": end.isoformat()},
                     "metrics": {}}
    for name, expression in promql.items():
        try:
            payload = client.get("prometheus", "/api/v1/query_range", {
                "query": expression, "start": str(int(start.timestamp())),
                "end": str(int(end.timestamp())), "step": "300s",
            })
            if not isinstance(payload, dict) or payload.get("status") != "success":
                raise QueryError(f"Prometheus did not complete {name}")
            series = payload.get("data", {}).get("result", [])
            state = metric_coverage(series, end.timestamp())
            results["metrics"][name] = {"state": state,
                                         "query": expression, "series": series}
        except QueryError as exc:
            results["metrics"][name] = {"state": "query_error", "query": expression,
                                         "error": str(exc)}
    for name, path in (("targets", "/api/v1/targets"), ("rules", "/api/v1/rules"),
                       ("alerts", "/api/v1/alerts")):
        try:
            results[name] = client.get("prometheus", path)
        except QueryError as exc:
            results[name] = {"error": str(exc)}
    active_targets = results.get("targets", {}).get("data", {}).get("activeTargets")
    if isinstance(active_targets, list) and results["metrics"]["scrape_up"]["state"] != "query_error":
        results["metrics"]["scrape_up"]["state"] = scrape_target_coverage(
            results["metrics"]["scrape_up"]["series"], active_targets,
            end.timestamp(), args.env, args.cluster)
    for name, path in (("loki", "/ready"), ("tempo", "/ready")):
        try:
            results[name] = client.get(name, path)
        except QueryError as exc:
            results[name] = {"error": str(exc)}
    recent = end - timedelta(hours=min(hours, 1))
    for name, path, params in (
        ("loki_recent", "/loki/api/v1/query_range", {
            "query": "{environment=" + json.dumps(args.env) + "}",
            "start": str(ns(recent)), "end": str(ns(end)),
            "direction": "backward", "limit": "1",
        }),
        ("tempo_recent", "/api/search", {
            "q": "{ resource.deployment.environment.name = " + json.dumps(args.env) + " }",
            "start": str(int(recent.timestamp())),
            "end": str(int(end.timestamp())), "limit": "1",
        }),
    ):
        backend = name.split("_")[0]
        try:
            payload = client.get(backend, path, params)
            entries = payload.get("traces", []) if backend == "tempo" else payload.get("data", {}).get("result", [])
            results[name] = {"state": "observed" if entries else "idle", "sample": entries[:1]}
        except QueryError as exc:
            results[name] = {"error": str(exc)}
    log_window = f"[{hours}h]"
    log_cluster = " | cluster=" + json.dumps(args.cluster) if args.cluster else ""
    for name, query in {
        "storage_failures": "sum(count_over_time({environment=" + json.dumps(args.env) + "} | k8s_container_name=\"agent\" | decolorize | logfmt" + log_cluster + " | event=\"storage.failed\" " + log_window + "))",
        "app_abnormal_exits": "sum(count_over_time({environment=" + json.dumps(args.env) + "} | json" + log_cluster + " | event=\"process.exited\" | outcome=\"error\" " + log_window + "))",
    }.items():
        try:
            payload = client.get("loki", "/loki/api/v1/query", {"query": query})
            if payload.get("status") != "success":
                raise QueryError(f"Loki did not complete {name}")
            series = payload.get("data", {}).get("result", [])
            results.setdefault("log_event_counts", {})[name] = {
                "state": "data" if series else "idle", "query": query,
                "count": sum(float(item["value"][1]) for item in series),
            }
        except (QueryError, ValueError, KeyError, IndexError, TypeError) as exc:
            results.setdefault("log_event_counts", {})[name] = {"error": str(exc), "query": query}
    for name, field in (("pending_upload_tasks", "pending_tasks"),
                        ("pending_upload_bytes", "pending_bytes")):
        query = ("max by (cluster,instance_id,branch_id) (last_over_time({environment="
                 + json.dumps(args.env) + "} | k8s_container_name=\"agent\""
                 + " |= \"event=storage.stats\" | logfmt | cluster=~"
                 + json.dumps(args.cluster or ".*") + " | unwrap " + field + " [5m]))")
        try:
            payload = client.get("loki", "/loki/api/v1/query", {"query": query})
            if payload.get("status") != "success":
                raise QueryError(f"Loki did not complete {name}")
            series = payload.get("data", {}).get("result", [])
            results.setdefault("storage_stats", {})[name] = {
                "state": "data" if series else "idle", "query": query, "series": series,
            }
        except QueryError as exc:
            results.setdefault("storage_stats", {})[name] = {"state": "query_error", "query": query, "error": str(exc)}
    root = output_dir(args, "inspect")
    (root / "metrics.json").write_text(json_text(results) + "\n", encoding="utf-8")
    failed = [key for key, value in results.items() if isinstance(value, dict) and "error" in value]
    failed += ["log_event_counts." + key for key, value in results.get("log_event_counts", {}).items() if "error" in value]
    failed += ["storage_stats." + key for key, value in results.get("storage_stats", {}).items() if "error" in value]
    missing = [key for key, value in results["metrics"].items() if value["state"] != "data"]
    latest: dict[str, list[float]] = {}
    for name, metric in results["metrics"].items():
        values = []
        for series in metric.get("series", []):
            samples = series.get("values", [])
            if samples and end.timestamp() - float(samples[-1][0]) <= 120:
                try:
                    value = float(samples[-1][1])
                    if math.isfinite(value):
                        values.append(value)
                except (ValueError, IndexError, TypeError):
                    pass
        latest[name] = values
    findings = []
    if any(value == 0 for value in latest.get("scrape_up", [])):
        findings.append("At least one published scrape target is down")
    for name in ("ingress_failures", "failed_tasks"):
        if any(value > 0 for value in latest.get(name, [])):
            findings.append(f"{name} has a recent nonzero rate")
    for name in ("collector_refused_spans", "collector_refused_logs",
                 "collector_enqueue_failed_logs", "collector_enqueue_failed_spans",
                 "collector_export_failed_logs", "collector_export_failed_spans"):
        if any(value > 0 for value in latest.get(name, [])):
            findings.append(f"{name} has a recent nonzero rate; incident evidence may be incomplete")
    if any(value >= 1 for value in latest.get("collector_queue_usage", [])):
        findings.append("At least one Collector exporter queue is full")
    for name, count in results.get("log_event_counts", {}).items():
        if count.get("count", 0) > 0:
            findings.append(f"{name}: {count['count']:g} events in the inspection window")
    for name, item in results.get("storage_stats", {}).items():
        for series in item.get("series", []):
            try:
                value = float(series["value"][1])
            except (KeyError, IndexError, TypeError, ValueError):
                continue
            if value > 0:
                labels = series.get("metric", {})
                findings.append(f"{name}: {value:g} on {labels.get('instance_id', 'unknown')}/{labels.get('branch_id', 'unknown')}")
    for series in results["metrics"].get("failed_agents", {}).get("series", []):
        samples = series.get("values", [])
        if not samples:
            continue
        try:
            count = float(samples[-1][1])
        except (ValueError, IndexError, TypeError):
            continue
        if math.isfinite(count) and count > 0:
            findings.append(f"Agent pool has {count:g} FAILED slots on {series.get('metric', {}).get('node_id', 'unknown')}")
    if any(value == 0 for value in latest.get("parked_agents", [])) and any(
            value > 0 for value in latest.get("configured_agents", [])):
        findings.append("A configured Agent pool has no PARKED capacity")
    alerts = results.get("alerts")
    if isinstance(alerts, dict) and alerts.get("status") == "success":
        active = [alert for alert in alerts.get("data", {}).get("alerts", [])
                  if alert.get("state") == "firing"]
        if active:
            findings.append(f"{len(active)} Prometheus alerts are firing")
    status = "incomplete" if failed or missing else ("attention" if findings else "normal")
    lines = ["# Daily inspection", "", f"Environment: {args.env}",
             f"Cluster: {args.cluster or 'all'}", f"Status: {status}",
             f"Scope: {results['scope']}",
             f"Window: {start.isoformat()} to {end.isoformat()}", "", "## Metric coverage", ""]
    lines += [f"- {name}: {value['state']}" for name, value in results["metrics"].items()]
    lines += ["", f"Backend failures: {', '.join(failed) if failed else 'none'}",
              f"Incomplete metric evidence: {', '.join(missing) if missing else 'none'}", "",
              "## Recent evidence", "",
              f"- Loki: {results.get('loki_recent', {}).get('state', 'query_error')}",
              f"- Tempo: {results.get('tempo_recent', {}).get('state', 'query_error')}", "",
              "## Log events", "",
              *[f"- {name}: {entry.get('count', 'query_error')}" for name, entry in results.get("log_event_counts", {}).items()], "",
              "## Storage uploads", "",
              *[f"- {name}: {entry['state']} ({len(entry.get('series', []))} instances)" for name, entry in results.get("storage_stats", {}).items()], "",
              "## Findings", ""]
    lines += [f"- {finding}" for finding in findings] if findings else ["- No rule-based finding from available data"]
    lines += ["",
              "Review metric values, alert state and target health in metrics.json. "
              "Data presence alone does not mean the system is healthy.", ""]
    (root / "diagnosis.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print(f"{status}: {root / 'diagnosis.md'}")
    return 2 if status == "incomplete" else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    def common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--env", required=True, help="Gaia environment name")
        sub.add_argument("--profile", help="Exported published Gaia diagnostic profile JSON")
        sub.add_argument("--output", help="Output evidence directory")

    common(commands.add_parser("doctor"))
    for command in ("request", "operation"):
        sub = commands.add_parser(command)
        sub.add_argument("identity", help="Exact request or operation ID")
        common(sub)
        sub.add_argument("--since", help="UTC ISO timestamp or Unix seconds")
        sub.add_argument("--until", help="UTC ISO timestamp or Unix seconds")
        if command == "operation":
            sub.add_argument("--component", required=True)
            sub.add_argument("--cluster", default="", help="Required for Control operation IDs; MGR job IDs are environment-scoped")
    inspect_parser = commands.add_parser("inspect")
    common(inspect_parser)
    inspect_parser.add_argument("--cluster", default="")
    inspect_parser.add_argument("--window", default="24h", help="Inspection window in whole hours, such as 1h or 24h (default: 24h)")
    args = parser.parse_args(argv)
    try:
        if args.command == "operation" and args.component == "control" and not args.cluster:
            raise QueryError("Control operation IDs require --cluster")
        profile = profile_for(args)
        client = Backend(profile)
        if args.command == "doctor":
            return doctor(args, profile, client)
        if args.command == "inspect":
            return inspect(args, profile, client)
        return investigate(args, profile, client)
    except QueryError as exc:
        print(f"tiana-debug: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
