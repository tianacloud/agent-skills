"""Behavioral tests for bounded incident searches and identity isolation."""

import json
import unittest
from unittest.mock import patch
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory

import tiana_debug as debug


class FakeBackend:
    def __init__(self, events=None, traces=None):
        self.events = events or []
        self.traces = traces or []
        self.queries = []

    def get(self, backend, path, params=None):
        self.queries.append((backend, path, params))
        if backend == "loki":
            selected = [event for event in self.events
                        if int(params["start"]) <= event[0] < int(params["end"])]
            selected = selected[:int(params["limit"])]
            return {"status": "success", "data": {"result": [
                {"stream": {"environment": "test"},
                 "values": [[str(stamp), line] for stamp, line in selected]}]}}
        if backend == "tempo":
            selected = [trace for stamp, trace in self.traces
                        if int(params["start"]) <= stamp < int(params["end"])]
            return {"traces": selected[:int(params["limit"])]}
        raise AssertionError(backend)


class SearchTests(unittest.TestCase):
    def test_logfmt_http_rejection_identifies_component_without_inventing_cause(self):
        line = 'event=request.completed component=gaia request_id=req-conflict status=409'
        fields = debug.attr_fields(line, {})
        record = {"fields": fields, "stream": {}, "time_unix_nano": "1"}
        finding = debug.failure_evidence([record], "req-conflict")
        self.assertEqual(finding["failure_component"], "gaia")
        self.assertEqual(finding["candidate_failure"]["http_status"], 409)
        self.assertIsNone(finding["root_cause_evidence"])

    def test_accepted_request_without_task_link_reports_gap(self):
        accepted = {"fields": {"component": "mgr", "event": "request.completed",
                   "status": 202, "request_id": "req-history", "trace_id": "trace-history"}}
        unrelated = {"fields": {"component": "mgr", "event": "task.link",
                    "request_id": "req-other", "trace_id": "trace-other",
                    "target_operation_id": "42", "target_component": "control",
                    "target_cluster": "cluster"}}
        gaps = []
        debug.async_acceptance_gaps([accepted, unrelated], gaps)
        self.assertEqual(len(gaps), 1)
        self.assertIn("req-history", gaps[0])
        self.assertIn("task", gaps[0])
        for association in ({"request_id": "req-history"}, {"trace_id": "trace-history"}):
            linked = {"fields": dict(unrelated["fields"], **association)}
            gaps = []
            debug.async_acceptance_gaps([accepted, linked], gaps)
            self.assertEqual(gaps, [])
        gaps = []
        direct = {"fields": dict(accepted["fields"], status=200)}
        debug.async_acceptance_gaps([direct], gaps)
        self.assertEqual(gaps, [])

    def test_fractional_tempo_window_keeps_matching_trace(self):
        start = debug.instant("2026-09-25T10:34:15.184875Z")
        end = debug.instant("2026-09-25T10:34:15.188367Z")
        client = FakeBackend(traces=[(start.timestamp() + .001,
                                     {"traceID": "a" * 32})])
        gaps = []
        found = debug.search_traces(client, "tiana.request.id", "req-test",
                                    start, end, gaps)
        self.assertIn("a" * 32, found)
        self.assertEqual(gaps, [])
        params = client.queries[0][2]
        self.assertLess(int(params["start"]), int(params["end"]))

    def test_expiry_plan_identity_preserves_cluster_and_deadline(self):
        plan = '["i","b",1790294400000]'
        logs = [{"fields": {"component": "control", "cluster": cluster,
                  "operation_id": operation, "expiry_plan_id": identity}}
                for cluster, operation, identity in [
                    ("c1", "12", plan), ("c1", "13", plan),
                    ("c2", "13", plan), ("c1", "14", '["i","b",1790294401000]')]]
        identities = debug.task_ids(logs)
        self.assertIn(("expiry_plan_id", plan, "control", "c1"), identities)
        self.assertIn(("expiry_plan_id", plan, "control", "c2"), identities)
        self.assertIn(("expiry_plan_id", '["i","b",1790294401000]', "control", "c1"), identities)
        query = debug.log_query("test", "expiry_plan_id", plan, "control", "c1")
        self.assertIn('expiry_plan_id=' + json.dumps(plan), query)
        self.assertIn('cluster="c1"', query)


    def test_policy_cache_failure_needs_dependency_evidence(self):
        wrapper = {"time_unix_nano": "1", "stream": {}, "fields": {
            "component": "gateway", "event": "gateway.connect.failed",
            "reason": "PolicyCache", "request_id": "req-cache"}}
        diagnosis = debug.failure_evidence([wrapper], "req-cache")
        self.assertEqual(diagnosis["failure_component"], "gateway")
        self.assertIsNone(diagnosis["root_cause_evidence"])
        self.assertEqual(diagnosis["candidate_failure"]["reason"], "PolicyCache")
        dependency = {"time_unix_nano": "2", "stream": {}, "fields": {
            "component": "gateway", "event": "gateway.redis.failed",
            "reason": "Connection refused", "dependency": "redis",
            "server_address": "redis.test:6379", "request_id": "req-cache"}}
        diagnosis = debug.failure_evidence([wrapper, dependency], "req-cache")
        self.assertEqual(diagnosis["root_cause_evidence"]["dependency"], "redis")
        self.assertEqual(diagnosis["root_cause_evidence"]["reason"], "Connection refused")

    def test_activation_deadline_needs_downstream_evidence(self):
        timeout = {"time_unix_nano": "2", "stream": {}, "fields": {
            "component": "gateway", "event": "gateway.connect.failed",
            "reason": "Ensure(ActivationDeadline)", "request_id": "req-start"}}
        result = debug.failure_evidence([timeout], "req-start")
        self.assertIsNone(result["root_cause_evidence"])
        self.assertEqual(result["candidate_failure"]["reason"], "Ensure(ActivationDeadline)")
        cause = {"time_unix_nano": "1", "stream": {}, "fields": {
            "component": "agent", "event": "app.exec.failed", "error_code": "APP_EXEC_FAILED",
            "reason": "App binary must be an executable non-symlink", "request_id": "req-start"}}
        result = debug.failure_evidence([timeout, cause], "req-start")
        self.assertEqual(result["root_cause_evidence"]["component"], "agent")
        self.assertEqual(result["root_cause_evidence"]["detail"], cause["fields"]["reason"])

    def test_connection_timeout_and_unavailable_are_symptoms(self):
        def record(event, reason, **extra):
            return {"time_unix_nano": "2", "stream": {}, "fields": {
                "component": "gateway", "event": event, "reason": reason,
                "request_id": "req-exit", **extra}}
        timeout = record("connection.closed", "timeout", outcome="error")
        exited = {"time_unix_nano": "1", "stream": {}, "fields": {
            "component": "agent", "event": "process.exited", "exit_code": 0,
            "outcome": "success", "request_id": "req-exit"}}
        result = debug.failure_evidence([exited, timeout], "req-exit")
        self.assertIsNone(result["root_cause_evidence"])
        self.assertEqual(result["candidate_failure"]["reason"], "timeout")
        unavailable = record("gateway.connect.failed", "Handshake(NotOk(AppUnavailable))")
        rejected = record("request.rejected", "INSTANCE_UNAVAILABLE")
        result = debug.failure_evidence([unavailable, rejected], "req-exit")
        self.assertIsNone(result["root_cause_evidence"])
        self.assertEqual(len(result["failure_events"]), 2)
        cause = {"time_unix_nano": "1", "stream": {}, "fields": {
            "component": "agent", "event": "process.exited", "outcome": "error",
            "error": "signal: killed", "request_id": "req-exit"}}
        result = debug.failure_evidence([timeout, cause], "req-exit")
        self.assertEqual(result["root_cause_evidence"]["reason"], "signal: killed")

    def test_gateway_write_close_preserves_observation_without_claiming_cause(self):
        record = {"time_unix_nano": "1", "stream": {}, "fields": {
            "component": "gateway", "event": "connection.closed", "request_id": "req-stream",
            "outcome": "failed", "reason": "stream_closed", "stage": "client_write",
            "direction": "agent_to_client"}}
        result = debug.failure_evidence([record], "req-stream")
        self.assertEqual(result["failure_component"], "")
        self.assertIsNone(result["root_cause_evidence"])
        self.assertEqual(result["candidate_failure"]["stage"], "client_write")
        self.assertEqual(result["candidate_failure"]["direction"], "agent_to_client")

    def test_gateway_read_close_does_not_label_successful_sql_as_gateway_failure(self):
        record = {"time_unix_nano": "1", "stream": {}, "fields": {
            "component": "gateway", "event": "connection.closed", "request_id": "req-sql",
            "outcome": "failed", "reason": "unexpected_eof", "stage": "client_read",
            "direction": "client_to_agent"}}
        result = debug.failure_evidence([record], "req-sql")
        self.assertEqual(result["failure_component"], "")
        self.assertIsNone(result["root_cause_evidence"])
        self.assertEqual(result["candidate_failure"]["reason"], "unexpected_eof")

    def test_delete_task_wrappers_preserve_candidates_and_task_identity(self):
        events = []
        for component, event, reason, identity in [
            ("control", "task.attempt.finished", "STORE_DELETE_UNCONFIRMED: runtime returned HTTP 409 (INVALID_STATE_TRANSITION): conflict", {"operation_id": 122}),
            ("control", "task.completed", "STORE_DELETE_UNCONFIRMED", {"operation_id": 122}),
            ("mgr", "task.completed", "SYNC_UNAVAILABLE", {"job_id": 994}),
        ]:
            events.append({"time_unix_nano": "1", "stream": {}, "fields": {
                "component": component, "event": event, "reason": reason,
                "outcome": "failed", "cluster": "cross", **identity}})
        result = debug.failure_evidence(events)
        self.assertIsNone(result["root_cause_evidence"])
        self.assertEqual(len(result["failure_events"]), 3)
        self.assertEqual(result["candidate_failure"]["operation_id"], "122")
        direct = {"time_unix_nano": "2", "stream": {}, "fields": {
            "component": "agent", "event": "app.exec.failed", "error_code": "APP_EXEC_FAILED",
            "reason": "App binary must be an executable non-symlink"}}
        result = debug.failure_evidence(events + [direct])
        self.assertEqual(result["root_cause_evidence"]["component"], "agent")

    def test_connection_trace_requires_gateway_root_when_agent_route_exists(self):
        def batch(service, name):
            return {"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": service}}]},
                    "scopeSpans": [{"spans": [{"name": name}]}]}
        agent = batch("tiana-agent", "agent.session.establish_route")
        gateway = batch("tiana-gateway", "gateway.session.establish")
        gaps = []
        debug.connection_trace_gaps({"trace-a": {"batches": [agent]}}, gaps)
        self.assertTrue(any("trace-a" in gap and "Gateway" in gap for gap in gaps))
        gaps = []
        debug.connection_trace_gaps({"trace-a": {"batches": [agent, gateway]}}, gaps)
        self.assertEqual(gaps, [])
        debug.connection_trace_gaps({"trace-b": {"batches": [gateway]}}, gaps)
        self.assertEqual(gaps, [])
        debug.connection_trace_gaps({"trace-c": {"batches": [batch("tiana-agent", "agent.app.stop")]}}, gaps)
        self.assertEqual(gaps, [])
        debug.connection_trace_gaps({"trace-a": {"batches": [agent]}, "trace-b": {"batches": [gateway]}}, gaps)
        self.assertTrue(any("trace-a" in gap for gap in gaps))
        gaps = []
        debug.connection_trace_gaps({"trace-fetch": {"batches": [agent, batch("tiana-gateway", "gateway.fetch")]}}, gaps)
        self.assertEqual(gaps, [])

    def test_connection_close_log_detects_missing_establish_spans(self):
        logs = [{"fields": {"component": "gateway", "event": "connection.closed", "trace_id": "trace-a"}}]
        gaps = []
        debug.connection_trace_gaps({"trace-a": {"batches": []}}, gaps, logs)
        self.assertTrue(any("trace-a" in gap and "Gateway" in gap for gap in gaps))
        gaps = []
        debug.connection_trace_gaps({"trace-b": {"batches": []}}, gaps, logs)
        self.assertEqual(gaps, [])
        gaps = []
        debug.connection_trace_gaps({"trace-a": {"batches": []}}, gaps,
            [{"fields": {"component": "agent", "event": "app.stopped", "trace_id": "trace-a"}}])
        self.assertEqual(gaps, [])

    def test_recovered_span_requires_exact_task_identity(self):
        span = {"component": "tiana-control", "operation_id": "1017", "job_id": "",
                "cluster": "cluster-a"}
        task = {"component": "control", "kind": "operation_id", "identity": "1017",
                "cluster": "cluster-a", "state": "success"}
        self.assertTrue(debug.recovered_task_span(span, [task]))
        for changes in ({"state": "failed"}, {"identity": "1018"},
                        {"cluster": "cluster-b"}, {"component": "mgr"}):
            self.assertFalse(debug.recovered_task_span(span, [dict(task, **changes)]))
        self.assertFalse(debug.recovered_task_span(dict(span, operation_id=""), [task]))

    def test_gaia_recovered_attempt_keeps_task_identity(self):
        finding = {"component": "gaia", "event": "task.attempt.completed",
                   "operation_id": "op-restarted", "cluster": "cluster-a"}
        task = {"component": "gaia", "kind": "operation_id", "identity": "op-restarted",
                "cluster": "cluster-a", "state": "succeeded"}
        self.assertTrue(debug.recovered_attempt(finding, [task]))
        for changes in ({"state": "failed"}, {"identity": "op-other"},
                        {"cluster": "cluster-b"}, {"component": "control"}):
            self.assertFalse(debug.recovered_attempt(finding, [dict(task, **changes)]))
        self.assertFalse(debug.recovered_attempt(dict(finding, event="request.failed"), [task]))

    def test_gaia_event_pages_and_query_failure_keep_evidence_state(self):
        args = Namespace(command="operation", identity="op-paged", component="gaia", cluster="", env="test", since=None, until=None)
        class GaiaBackend(FakeBackend):
            def __init__(self, fail):
                super().__init__()
                self.fail = fail
            def get(self, backend, path, params=None):
                self.queries.append((backend, path, params))
                if path.endswith("/events"):
                    if params["after"] == 0:
                        return {"items": [{"sequence": n} for n in range(1, 201)]}
                    if self.fail:
                        raise debug.QueryError("Gaia events query unavailable")
                    return {"items": [{"sequence": 201}]}
                return {"operation_id": "op-paged", "state": "FAILED", "step": "probe", "error_code": "STEP_FAILED"}
        for fail in (False, True):
            with self.subTest(fail=fail), TemporaryDirectory() as directory, \
                 patch.object(debug, "search_logs", return_value=[]), \
                 patch.object(debug, "search_traces", return_value={}), \
                 patch.object(debug, "output_dir", return_value=Path(directory)):
                client = GaiaBackend(fail)
                self.assertEqual(debug.investigate(args, {"retention_hours": 168}, client), 2)
                events = json.loads((Path(directory)/"gaia_events.json").read_text())
                self.assertEqual(len(events["op-paged"]), 200 if fail else 201)
                self.assertEqual(client.queries[-1][2], {"after": 200})
                summary = json.loads((Path(directory)/"evidence.json").read_text())
                self.assertEqual(any("Gaia events query unavailable" in gap for gap in summary["gaps"]), fail)

    def test_request_reads_each_linked_gaia_operation(self):
        args = Namespace(command="request", identity="req-gaia", env="test", since=None, until=None)
        logs = [{"time_unix_nano": str(i+1), "stream": {}, "line": "linked", "fields": {
            "request_id": "req-gaia", "component": "gaia", "operation_id": identity,
            "event": "task.link", "cluster": "cluster-"+identity}}
            for i, identity in enumerate(("op-a", "op-b"))]
        class GaiaBackend(FakeBackend):
            def get(self, backend, path, params=None):
                self.queries.append((backend, path, params))
                if path.endswith("/events"):
                    return {"items": [{"sequence": 1, "step": "wait_self_registration", "message": "timeout"}]}
                return {"operation_id": path.rsplit("/", 1)[-1], "state": "FAILED",
                        "step": "wait_self_registration", "error_code": "STEP_FAILED", "error_message": "timeout"}
        client = GaiaBackend()
        with TemporaryDirectory() as directory, \
             patch.object(debug, "search_logs", return_value=logs), \
             patch.object(debug, "search_traces", return_value={}), \
             patch.object(debug, "output_dir", return_value=Path(directory)):
            self.assertEqual(debug.investigate(args, {"retention_hours": 168}, client), 2)
            summary = json.loads((Path(directory)/"evidence.json").read_text())
            self.assertEqual({item["operation_id"] for item in summary["gaia_operations"]}, {"op-a", "op-b"})
            report = (Path(directory)/"diagnosis.md").read_text()
            self.assertIn("op-a", report)
            self.assertIn("op-b", report)
            self.assertIn("No matching Tempo", report)
        self.assertEqual(len(client.queries), 4)

    def test_redaction_preserves_nested_json_evidence(self):
        record = {"fields": {"business_request_id": "cli-token:fixture:1"},
                  "line": json.dumps({"business_request_id": "cli-token:fixture:1",
                                      "event": "task.completed", "job_id": 42}),
                  "messages": ["password=fixture-secret"]}
        saved = debug.json_text(record)
        decoded = json.loads(saved)
        self.assertEqual(decoded["fields"]["business_request_id"], "cli-token:[REDACTED]")
        self.assertEqual(json.loads(decoded["line"])["job_id"], 42)
        self.assertEqual(decoded["messages"], ["password=[REDACTED]"])
        self.assertEqual(record["messages"], ["password=fixture-secret"])

    def test_colored_app_error_preserves_identity_and_severity(self):
        line = ('cluster="c1" tenant_id="t1" instance_id="i1" branch_id="main" '
                '\x1b[2m2026-09-24T12:09:36.512177Z\x1b[0m \x1b[31mERROR\x1b[0m '
                'app_sqlite: versioned-fs startup failed \x1b[3merror\x1b[0m=lock_timeout')
        fields = debug.attr_fields(line, {})
        self.assertEqual(fields["level"], "error")
        self.assertEqual(fields["instance_id"], "i1")
        self.assertEqual(fields["error"], "lock_timeout")

    def test_resource_candidates_keep_branch_and_tenant_scope(self):
        fields = {"cluster": "c1", "instance_id": "i1", "branch_id": "main", "tenant_id": "t1"}
        direct = {"time_unix_nano": "1", "fields": fields, "line": "known request"}
        candidate = {"time_unix_nano": "2", "fields": dict(fields),
                     "stream": {"detected_level": "error"}, "line": "App startup lock timeout"}
        other_branch = dict(candidate, fields=dict(fields, branch_id="other"))
        other_tenant = dict(candidate, fields=dict(fields, tenant_id="other"))
        start, end = debug.instant("2026-09-24T00:00:00Z"), debug.instant("2026-09-24T00:01:00Z")
        with patch.object(debug, "search_logs", return_value=[candidate, other_branch, other_tenant, direct]) as query:
            found = debug.resource_failure_candidates(FakeBackend(), "test", [direct], start, end, [])
        self.assertEqual(found, [candidate])
        self.assertEqual(query.call_args.args[2:4], ("instance_id", "i1"))
        self.assertEqual(query.call_args.kwargs, {"cluster": "c1"})
        self.assertIsNone(debug.failure_evidence([direct])["root_cause_evidence"])

    def test_successful_transport_still_finds_sql_rejection_candidate(self):
        args = Namespace(command="request", identity="req-sql", env="test", since=None, until=None)
        identity = {"cluster": "c1", "instance_id": "i1", "branch_id": "main", "tenant_id": "t1"}
        direct = {"time_unix_nano": "1", "stream": {}, "line": "transport closed normally",
                  "fields": dict(identity, request_id="req-sql", component="gateway", event="connection.closed")}
        rejected = {"time_unix_nano": "2", "stream": {}, "line": "Hrana request failed",
                    "fields": dict(identity, component="app_sqlite", event="request.failed", error_code="STREAM_LIMIT")}
        def search(client, env, field, value, *args, **kwargs):
            return [rejected] if field == "instance_id" else [direct]
        with TemporaryDirectory() as directory, \
             patch.object(debug, "search_logs", side_effect=search), \
             patch.object(debug, "search_traces", return_value={}), \
             patch.object(debug, "output_dir", return_value=Path(directory)), \
             patch.object(debug, "evidence_files") as evidence:
            self.assertEqual(debug.investigate(args, {"retention_hours": 168}, FakeBackend()), 2)
            summary = evidence.call_args.args[1]
            self.assertEqual(summary["resource_candidates"], [rejected])
            self.assertIsNone(summary["diagnosis"]["root_cause_evidence"])

    def test_resource_candidate_backend_gap_is_preserved(self):
        direct = {"time_unix_nano": "1", "fields": {"cluster": "c1", "instance_id": "i1"}, "line": "request"}
        gaps = []
        def incomplete(client, env, field, value, start, end, query_gaps, **kwargs):
            query_gaps.append("Loki saturated at nanosecond 1")
            return []
        with patch.object(debug, "search_logs", side_effect=incomplete):
            found = debug.resource_failure_candidates(FakeBackend(), "test", [direct], None, None, gaps)
        self.assertEqual(found, [])
        self.assertEqual(gaps, ["Loki saturated at nanosecond 1"])

    def test_idle_histogram_nan_and_partial_series_remain_incomplete(self):
        finite = {"values": [[1000, "0.12"]]}
        idle = {"values": [[1000, "NaN"]]}
        stale = {"values": [[100, "0.1"]]}
        self.assertEqual(debug.metric_coverage([idle], 1000), "no_samples")
        self.assertEqual(debug.metric_coverage([finite, idle], 1000), "partial")
        self.assertEqual(debug.metric_coverage([finite, stale], 1000), "partial")
        self.assertEqual(debug.metric_coverage([stale], 1000), "stale")
        self.assertEqual(debug.metric_coverage([], 1000), "missing")
        self.assertEqual(debug.metric_coverage([finite], 1000), "data")

    def test_scrape_coverage_uses_current_targets_after_pod_replacement(self):
        current = {"environment": "test", "job": "mgr", "instance": "pod-new"}
        retired = {"environment": "test", "job": "mgr", "instance": "pod-old"}
        series = [
            {"metric": {"__name__": "up", **current}, "values": [[1000, "1"]]},
            {"metric": {"__name__": "up", **retired}, "values": [[800, "1"]]},
        ]
        targets = [{"labels": current, "health": "up"}]
        self.assertEqual(debug.scrape_target_coverage(series, targets, 1000, "test", None), "data")
        missing = {"environment": "test", "job": "gateway", "instance": "pod-new"}
        self.assertEqual(debug.scrape_target_coverage(series, targets + [{"labels": missing, "health": "down"}], 1000, "test", None), "partial")

    def test_requested_stream_failure_precedes_linked_task_retry(self):
        logs = [{"time_unix_nano": "1", "stream": {}, "fields": {
            "component": "control", "event": "task.attempt.finished", "outcome": "failed",
            "operation_id": 607, "reason": "stop accepted"}},
            {"time_unix_nano": "2", "stream": {}, "fields": {
            "component": "mgr", "event": "connection.closed", "outcome": "failed",
            "request_id": "req-stream", "reason": "upstream_closed"}}]
        diagnosis = debug.failure_evidence(logs, "req-stream")
        self.assertEqual(diagnosis["root_cause_evidence"]["reason"], "upstream_closed")
        self.assertEqual(len(diagnosis["failure_events"]), 2)
        self.assertEqual(debug.failure_evidence(logs)["root_cause_evidence"]["reason"], "stop accepted")


    def test_downstream_failure_retains_observed_target(self):
        result = debug.failure_evidence([{"time_unix_nano": "1", "stream": {}, "fields": {
            "event": "gateway.http.response.failed", "component": "gateway",
            "request_id": "req-directory", "outcome": "failed",
            "reason": "HTTP 503 response rejected: Body(InvalidJson)",
            "server_address": "directory.test", "path": "/directory/v1/endpoint-homes/ep-test"}}], "req-directory")
        self.assertEqual(result["failure_component"], "gateway")
        self.assertEqual(result["root_cause_evidence"]["server_address"], "directory.test")
        self.assertEqual(result["root_cause_evidence"]["path"], "/directory/v1/endpoint-homes/ep-test")

    def test_recovery_is_scoped_to_failed_attempt_task(self):
        finding = debug.failure_evidence([{"time_unix_nano": "1", "stream": {}, "fields": {
            "event": "task.attempt.finished", "component": "control", "cluster": "east",
            "operation_id": 563, "outcome": "failed", "reason": "no Runtime"}}])["root_cause_evidence"]
        tasks = [{"kind": "job_id", "identity": "426", "component": "mgr", "cluster": "east", "state": "success"}]
        self.assertFalse(debug.recovered_attempt(finding, tasks))
        task = {"kind": "operation_id", "identity": "563", "component": "control", "cluster": "east", "state": "success"}
        self.assertTrue(debug.recovered_attempt(finding, tasks + [task]))
        for changes in [{"cluster": "west"}, {"state": "failed"}, {"identity": "564"}]:
            self.assertFalse(debug.recovered_attempt(finding, tasks + [dict(task, **changes)]))
        self.assertFalse(debug.recovered_attempt(dict(finding, event="request.failed"), tasks + [task]))


    def test_tempo_and_log_ids_identify_the_same_full_trace(self):
        full = "07e6a9d7824500e641006bc1221376ee"
        client = FakeBackend(traces=[(1, {"traceID": full.lstrip("0")})])
        hits, gaps = {}, []
        debug.tempo_window(client, "tiana.request.id", "req", 0, 2, hits, gaps)
        ids = set(hits) | {debug.canonical_trace_id(full)}
        self.assertEqual(ids, {full})
        self.assertEqual(gaps, [])


    def test_app_error_response_is_evidence_without_inventing_root_cause(self):
        for status in [404, 500]:
            result = debug.failure_evidence([{"time_unix_nano": "1", "stream": {}, "fields": {
                "component": "gateway", "event": "connection.closed", "outcome": "success",
                "reason": "eof", "app_http_status": status, "request_id": "req-app"}}])
            self.assertEqual(result["failure_component"], "app")
            self.assertIsNone(result["root_cause_evidence"])
            self.assertEqual(result["candidate_failure"]["http_status"], status)

    def test_loki_splits_full_pages_and_keeps_boundary_events(self):
        old_limit = debug.PAGE_LIMIT
        debug.PAGE_LIMIT = 2
        try:
            client = FakeBackend(events=[
                (2, '{"event":"a","request_id":"req"}'),
                (5, '{"event":"b","request_id":"req"}'),
                (8, '{"event":"c","request_id":"req"}'),
            ])
            records, gaps = {}, []
            debug.loki_window(client, debug.log_query("test", "request_id", "req"),
                              0, 10, records, gaps)
            self.assertEqual([record["fields"]["event"] for record in records.values()],
                             ["a", "b", "c"])
            self.assertEqual(gaps, [])
        finally:
            debug.PAGE_LIMIT = old_limit

    def test_loki_reports_indistinguishable_timestamp_saturation(self):
        old_limit = debug.PAGE_LIMIT
        debug.PAGE_LIMIT = 2
        try:
            client = FakeBackend(events=[(5, "one"), (5, "two"), (5, "three")])
            records, gaps = {}, []
            debug.loki_window(client, debug.log_query("test", "request_id", "req"),
                              5, 6, records, gaps)
            self.assertEqual(len(records), 2)
            self.assertEqual(len(gaps), 1)
            self.assertIn("saturated", gaps[0])
        finally:
            debug.PAGE_LIMIT = old_limit

    def test_tempo_reports_saturation_at_one_second(self):
        old_limit = debug.TRACE_LIMIT
        debug.TRACE_LIMIT = 2
        try:
            client = FakeBackend(traces=[
                (5, {"traceID": "1"}), (5, {"traceID": "2"}),
                (5, {"traceID": "3"}),
            ])
            traces, gaps = {}, []
            debug.tempo_window(client, "tiana.request.id", "req", 5, 6, traces, gaps)
            self.assertEqual(set(traces), {"1", "2"})
            self.assertEqual(len(gaps), 1)
        finally:
            debug.TRACE_LIMIT = old_limit

    def test_tempo_preserves_subsecond_traces_across_page_boundaries(self):
        old_limit = debug.TRACE_LIMIT
        debug.TRACE_LIMIT = 3
        try:
            client = FakeBackend(traces=[
                (0.9, {"traceID": "1"}), (1.9, {"traceID": "2"}),
                (2.9, {"traceID": "3"}), (3.9, {"traceID": "4"}),
            ])
            traces, gaps = {}, []
            debug.tempo_window(client, "tiana.request.id", "req", 0, 4, traces, gaps)
            self.assertEqual(set(traces), {"1", "2", "3", "4"})
            self.assertEqual(gaps, [])
            self.assertTrue(all(q[2]["start"] < q[2]["end"] for q in client.queries))
        finally:
            debug.TRACE_LIMIT = old_limit

    def test_operation_query_uses_component_and_cluster(self):
        query = debug.log_query("test", "operation_id", "42", "control", "cluster-a")
        self.assertIn("| json | logfmt |", query)
        self.assertIn('component="control"', query)
        self.assertIn('cluster="cluster-a"', query)

    def test_control_task_log_keeps_identity_and_reason(self):
        fields = debug.attr_fields(
            '2026/09/23 INFO Control operation attempt finished event=task.attempt.finished component=control '
            'operation_id=139 instance_id=inst-a branch_id=main outcome=failed reason="snapshot worker ended"', {})
        self.assertEqual(fields["operation_id"], "139")
        self.assertEqual(fields["branch_id"], "main")
        self.assertEqual(debug.failure_evidence([{"time_unix_nano": "1", "stream": {},
                                                  "fields": fields}])["root_cause_evidence"]["reason"],
                         "snapshot worker ended")

    def test_failure_finding_requires_structured_reason(self):
        records = [
            {"time_unix_nano": "1", "stream": {"component": "gateway"},
             "fields": {"event": "request.failed", "request_id": "req"}},
            {"time_unix_nano": "2", "stream": {"component": "control"},
             "fields": {"event": "activation.failed", "error_kind": "NoParkedAgent",
                        "trace_id": "abcd"}},
        ]
        finding = debug.failure_evidence(records)
        self.assertEqual(finding["failure_component"], "control")
        self.assertEqual(finding["root_cause_evidence"]["reason"], "NoParkedAgent")
        self.assertEqual(len(finding["failure_events"]), 2)

    def test_failed_span_keeps_http_status_and_does_not_invent_root_cause(self):
        traces = {"abc": {"batches": [{"resource": {"attributes": [
            {"key": "service.name", "value": {"stringValue": "mgr"}}]},
            "scopeSpans": [{"spans": [{"name": "call.post.request", "spanId": "child",
                "parentSpanId": "parent", "startTimeUnixNano": "10", "endTimeUnixNano": "20",
                "status": {"code": "STATUS_CODE_ERROR", "message": "server_error"},
                "attributes": [{"key": "http.response.status_code", "value": {"intValue": "503"}}]}]}]}]}}
        diagnosis = debug.failure_evidence([])
        debug.add_span_findings(diagnosis, traces)
        self.assertEqual(diagnosis["span_failures"][0]["http_status"], "503")
        self.assertEqual(diagnosis["span_failures"][0]["parent_span_id"], "parent")
        self.assertEqual(diagnosis["failure_component"], "mgr")
        self.assertEqual(diagnosis["candidate_failure"]["kind"], "span")
        self.assertIsNone(diagnosis["root_cause_evidence"])

    def test_request_does_not_expand_an_unowned_numeric_task(self):
        args = Namespace(command="request", identity="req-17", env="test", since=None, until=None)
        logs = [{"time_unix_nano": "1", "stream": {}, "line": "linked", "fields": {
            "request_id": "req-17", "job_id": "17", "event": "task.link"}}]
        with TemporaryDirectory() as directory, \
             patch.object(debug, "search_logs", return_value=logs) as search, \
             patch.object(debug, "search_traces", return_value={}), \
             patch.object(debug, "output_dir", return_value=Path(directory)), \
             patch.object(debug, "evidence_files") as evidence:
            self.assertEqual(debug.investigate(args, {"retention_hours": 168}, FakeBackend()), 2)
            self.assertEqual(search.call_count, 1)
            self.assertTrue(any("owning component" in gap for gap in evidence.call_args.args[1]["gaps"]))

    def test_failure_keeps_provider_detail_with_public_error_code(self):
        result = debug.failure_evidence([{"time_unix_nano": "1", "stream": {}, "fields": {
            "component": "mgr", "event": "auth.social.failed", "error_code": "AUTH_PROVIDER_ERROR",
            "reason": "provider authorization denied", "request_id": "req-denied"}}], "req-denied")
        self.assertEqual(result["root_cause_evidence"]["reason"], "AUTH_PROVIDER_ERROR")
        self.assertEqual(result["root_cause_evidence"]["detail"], "provider authorization denied")

    def test_auth_transaction_denial_is_an_observed_terminal_state(self):
        args = Namespace(command="request", identity="req-poll", env="test", since=None, until=None)
        def record(stamp, **fields):
            return {"time_unix_nano": str(stamp), "stream": {}, "line": str(fields), "fields": fields}
        poll = record(2, component="mgr", request_id="req-poll", transaction_id="at-1", event="auth.transaction.link", phase="poll")
        denied = record(1, component="mgr", request_id="req-deny", transaction_id="at-1", event="auth.transaction.link", phase="auth.transaction.denied")
        def search(client, env, field, identity, *rest):
            return {("request_id", "req-poll"): [poll], ("transaction_id", "at-1"): [denied, poll]}[(field, identity)].copy()
        with TemporaryDirectory() as directory, \
             patch.object(debug, "search_logs", side_effect=search), \
             patch.object(debug, "search_traces", return_value={}), \
             patch.object(debug, "output_dir", return_value=Path(directory)), \
             patch.object(debug, "evidence_files") as evidence:
            debug.investigate(args, {"retention_hours": 168}, FakeBackend())
            diagnosis = evidence.call_args.args[1]["diagnosis"]
            self.assertEqual(diagnosis["terminal_state"], "denied")
            self.assertEqual(diagnosis["task_terminal_states"][0]["request_id"], "req-deny")
            self.assertIsNone(diagnosis["root_cause_evidence"])

    def test_social_request_expands_transaction_across_callback(self):
        args = Namespace(command="request", identity="req-start", env="test", since=None, until=None)
        def record(stamp, **fields):
            return {"time_unix_nano": str(stamp), "stream": {}, "line": str(fields), "fields": fields}
        start = record(1, component="mgr", request_id="req-start", transaction_id="soc-1", event="auth.social.link")
        callback = record(2, component="mgr", request_id="req-callback", transaction_id="soc-1", event="auth.social.link")
        def search(client, env, field, identity, *rest):
            return {("request_id", "req-start"): [start], ("transaction_id", "soc-1"): [start, callback]}[(field, identity)].copy()
        with TemporaryDirectory() as directory, \
             patch.object(debug, "search_logs", side_effect=search) as logs, \
             patch.object(debug, "search_traces", return_value={}), \
             patch.object(debug, "output_dir", return_value=Path(directory)), \
             patch.object(debug, "evidence_files") as evidence:
            debug.investigate(args, {"retention_hours": 168}, FakeBackend())
            self.assertEqual(evidence.call_args.args[1]["task_ids"], [["transaction_id", "soc-1", "mgr", ""]])
            self.assertEqual(len(evidence.call_args.args[2]), 2)
            self.assertIn('transaction_id="soc-1"', debug.log_query("test", "transaction_id", "soc-1", "mgr"))

    def test_support_request_expands_collaboration_then_delivery(self):
        args = Namespace(command="request", identity="req-support", env="test", since=None, until=None)
        def record(stamp, **fields):
            return {"time_unix_nano": str(stamp), "stream": {}, "line": str(fields), "fields": fields}
        linked = record(1, component="support", request_id="req-support", collaboration_id="collab-1", event="task.link")
        delivery = record(2, component="support", collaboration_id="collab-1", operation_id="delivery-1", event="task.attempt.started")
        complete = record(3, component="support", operation_id="delivery-1", event="task.completed", outcome="success")
        def search(client, env, field, identity, *rest):
            return {("request_id", "req-support"): [linked],
                    ("collaboration_id", "collab-1"): [delivery],
                    ("operation_id", "delivery-1"): [complete]}[(field, identity)].copy()
        with TemporaryDirectory() as directory, \
             patch.object(debug, "search_logs", side_effect=search), \
             patch.object(debug, "search_traces", return_value={}), \
             patch.object(debug, "output_dir", return_value=Path(directory)), \
             patch.object(debug, "evidence_files") as evidence:
            debug.investigate(args, {"retention_hours": 168}, FakeBackend())
            summary = evidence.call_args.args[1]
            self.assertEqual(summary["task_ids"], [["collaboration_id", "collab-1", "support", ""], ["operation_id", "delivery-1", "support", ""]])
            states = summary["diagnosis"]["task_terminal_states"]
            self.assertEqual(len(states), 1)
            self.assertEqual(states[0]["identity"], "delivery-1")

    def test_failed_task_result_read_failure_is_explicitly_incomplete(self):
        args = Namespace(command="request", identity="req-failed", env="test", since=None, until=None)
        logs = [{"time_unix_nano": "1", "stream": {}, "line": "failed", "fields": {
            "component": "control", "cluster": "east", "operation_id": "7",
            "event": "task.completed", "outcome": "failed",
            "diagnostic_reason": "operation_result_unavailable"}}]
        with TemporaryDirectory() as directory, \
             patch.object(debug, "search_logs", return_value=logs), \
             patch.object(debug, "search_traces", return_value={}), \
             patch.object(debug, "output_dir", return_value=Path(directory)), \
             patch.object(debug, "evidence_files") as evidence:
            self.assertEqual(debug.investigate(args, {"retention_hours": 168}, FakeBackend()), 2)
            summary = evidence.call_args.args[1]
            self.assertTrue(any("operation result unavailable" in gap for gap in summary["gaps"]))
            self.assertIsNone(summary["diagnosis"]["root_cause_evidence"])

    def test_missing_diagnostic_linkage_marks_evidence_partial(self):
        args = Namespace(command="request", identity="req-support", env="test", since=None, until=None)
        logs = [{"time_unix_nano": "1", "stream": {}, "line": "missing", "fields": {
            "component": "support", "event": "telemetry.context.missing",
            "reason_code": "collaboration_lookup_failed", "request_id": "req-support"}}]
        with TemporaryDirectory() as directory, \
             patch.object(debug, "search_logs", return_value=logs), \
             patch.object(debug, "search_traces", return_value={}), \
             patch.object(debug, "output_dir", return_value=Path(directory)), \
             patch.object(debug, "evidence_files") as evidence:
            self.assertEqual(debug.investigate(args, {"retention_hours": 168}, FakeBackend()), 2)
            self.assertTrue(any("collaboration_lookup_failed" in gap for gap in evidence.call_args.args[1]["gaps"]))

    def test_long_connection_close_recovers_older_establishment_logs(self):
        now = debug.datetime.now(debug.UTC)
        opened = now - debug.timedelta(days=3)
        close = {"time_unix_nano": str(debug.ns(now)), "stream": {}, "line": "close",
                 "fields": {"event": "connection.closed", "request_id": "req-long", "duration_ms": 3 * 86400 * 1000}}
        establish = {"time_unix_nano": str(debug.ns(opened)), "stream": {}, "line": "establish",
                     "fields": {"event": "connection.established", "request_id": "req-long"}}
        args = Namespace(command="request", identity="req-long", env="test", since=None, until=None)
        def search(client, env, field, identity, start, end, *rest):
            return [establish] if start <= opened else [close]
        with TemporaryDirectory() as directory, \
             patch.object(debug, "search_logs", side_effect=search), \
             patch.object(debug, "search_traces", return_value={}), \
             patch.object(debug, "output_dir", return_value=Path(directory)), \
             patch.object(debug, "evidence_files") as evidence:
            debug.investigate(args, {"retention_hours": 168}, FakeBackend())
            self.assertEqual([r["line"] for r in evidence.call_args.args[2]], ["establish", "close"])
            self.assertLessEqual(debug.instant(evidence.call_args.args[1]["window"]["start"]), opened)

    def test_close_before_retention_keeps_evidence_and_reports_unavailable_start(self):
        now = debug.datetime.now(debug.UTC)
        floor = now - debug.timedelta(days=7)
        logs = [{"time_unix_nano": str(debug.ns(now)), "fields": {
            "event": "connection.closed", "duration_ms": 8 * 86400 * 1000}}]
        gaps = []
        expanded = debug.connection_window_start(logs, now - debug.DAY, floor, gaps)
        self.assertEqual(expanded, floor)
        self.assertEqual(len(gaps), 1)
        self.assertIn("before the available retention", gaps[0])

    def test_expired_window_returns_partial_evidence_without_backend_queries(self):
        now = debug.datetime.now(debug.UTC)
        args = Namespace(command="request", identity="req-expired", env="test",
                         since=(now - debug.timedelta(days=10)).isoformat(),
                         until=(now - debug.timedelta(days=9)).isoformat())
        backend = FakeBackend()
        with TemporaryDirectory() as directory, \
             patch.object(debug, "output_dir", return_value=Path(directory)), \
             patch.object(debug, "evidence_files") as evidence:
            self.assertEqual(debug.investigate(args, {"retention_hours": 168}, backend), 2)
            summary = evidence.call_args.args[1]
            self.assertEqual(summary["queries"], [])
            self.assertEqual(summary["status"], "partial")
            self.assertIsNone(summary["diagnosis"]["root_cause_evidence"])
            self.assertIn("entirely outside", summary["gaps"][0])

    def test_mgr_operation_uses_job_identity_and_reports_successful_cleanup(self):
        args = Namespace(command="operation", identity="17", component="mgr", cluster="",
                         env="test", since=None, until=None)
        logs = [{"time_unix_nano": "1", "stream": {}, "line": "completed", "fields": {
            "component": "mgr", "job_id": "17", "event": "task.completed", "outcome": "success"}}]
        with TemporaryDirectory() as directory, \
             patch.object(debug, "search_logs", return_value=logs.copy()) as search, \
             patch.object(debug, "search_traces", return_value={}) as traces, \
             patch.object(debug, "output_dir", return_value=Path(directory)), \
             patch.object(debug, "evidence_files") as evidence:
            debug.investigate(args, {"retention_hours": 168}, FakeBackend())
            self.assertEqual(search.call_args_list[0].args[2], "job_id")
            self.assertEqual(traces.call_args_list[0].args[1], "job_id")
            summary = evidence.call_args.args[1]
            self.assertEqual(summary["task_ids"], [["job_id", "17", "mgr", ""]])
            self.assertEqual(summary["diagnosis"]["terminal_state"], "success")

    def test_retry_reports_observed_failure_without_treating_pending_as_error(self):
        logs = [{"time_unix_nano": "1", "stream": {}, "fields": {
            "component": "mgr", "event": "task.attempt.finished", "outcome": "retry",
            "reason_code": "CONTROL_HTTP_ERROR"}},
            {"time_unix_nano": "2", "stream": {}, "fields": {
                "component": "mgr", "event": "task.attempt.finished", "outcome": "retry"}}]
        finding = debug.failure_evidence(logs)
        self.assertEqual(len(finding["failure_events"]), 1)
        self.assertEqual(finding["root_cause_evidence"]["reason"], "CONTROL_HTTP_ERROR")

    def test_control_503_from_mgr_identifies_failed_downstream_boundary(self):
        records = [{"time_unix_nano": "1", "stream": {"component": "mgr"}, "fields": {
            "component": "mgr", "event": "http.client.failed", "outcome": "failed",
            "error_code": "downstream_http_error", "status": 503,
            "server_address": "control-b.example.test",
            "path": "/control/v1/mgr/gateway-auth-command",
            "cluster": "cluster-b", "trace_id": "trace-a"}}]
        finding = debug.failure_evidence(records)
        self.assertEqual(finding["failure_component"], "control")
        self.assertEqual(finding["root_cause_evidence"]["component"], "mgr")
        self.assertEqual(finding["root_cause_evidence"]["server_address"],
                         "control-b.example.test")

    def test_control_business_result_identifies_target_component(self):
        records = [
            {"time_unix_nano": "1", "stream": {"component": "mgr"}, "fields": {
                "component": "mgr", "event": "task.target.failed", "outcome": "failed",
                "target_component": "control", "target_operation_id": "operation-42",
                "reason_code": "INSTANCE_TOMBSTONED", "job_id": 42,
                "cluster": "cluster-a", "trace_id": "attempt-trace"}},
            {"time_unix_nano": "2", "stream": {"component": "mgr"}, "fields": {
                "component": "mgr", "event": "task.attempt.finished", "outcome": "failed",
                "reason_code": "INSTANCE_TOMBSTONED", "job_id": 42,
                "cluster": "cluster-a", "trace_id": "attempt-trace"}},
        ]
        finding = debug.failure_evidence(records)
        self.assertEqual(finding["failure_component"], "control")
        self.assertEqual(finding["root_cause_evidence"]["target_operation_id"], "operation-42")
        self.assertEqual(finding["root_cause_evidence"]["reason"], "INSTANCE_TOMBSTONED")

    def test_outbound_failure_in_recovered_task_attempt_is_historical(self):
        records = [
            {"time_unix_nano": "1", "stream": {"component": "mgr"}, "fields": {
                "component": "mgr", "event": "http.client.failed", "outcome": "failed",
                "error_code": "downstream_http_error", "status": 503,
                "path": "/control/v1/mgr/gateway-auth-command", "trace_id": "attempt-trace",
                "cluster": "cluster-b"}},
            {"time_unix_nano": "2", "stream": {"component": "mgr"}, "fields": {
                "component": "mgr", "event": "task.attempt.finished", "job_id": 1244,
                "kind": "tenant_token_sync", "outcome": "retry",
                "reason_code": "CONTROL_HTTP_ERROR", "trace_id": "attempt-trace"}},
        ]
        finding = debug.failure_evidence(records)["root_cause_evidence"]
        completed = [{"kind": "job_id", "identity": "1244", "component": "mgr",
                      "cluster": "", "state": "success"}]
        self.assertTrue(debug.recovered_attempt(finding, completed))

    def test_rejected_request_uses_recorded_error_code(self):
        records = [{"time_unix_nano": "1", "stream": {"component": "mgr"},
                    "fields": {"event": "request.rejected", "component": "mgr",
                               "status": 401, "error_code": "AUTHENTICATION_REQUIRED"}}]
        finding = debug.failure_evidence(records)
        self.assertEqual(finding["failure_component"], "mgr")
        self.assertEqual(finding["root_cause_evidence"]["reason"], "AUTHENTICATION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
