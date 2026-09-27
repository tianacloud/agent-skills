import unittest
from datetime import datetime, timezone, timedelta

import tiana_debug as debug


class TraceparentLogsTest(unittest.TestCase):
    trace = "475576dac0eb1dda90a33ca0d4ecb1a4"
    parent = "00-475576dac0eb1dda90a33ca0d4ecb1a4-7ca0d5adb83860b9-01"
    line = ('region="dev" cluster="dev" tenant_id="tenant" instance_id="sqlite-fixture" '
            'branch_id="main" 2026-09-27T10:58:41.165821Z INFO versioned_fs: '
            '[2026-09-27T10:58:41Z INFO vfs::http_service] event=request.completed '
            'component=fs request_id="req-task" traceparent="' + parent + '" '
            'method="POST" route="/branches" status=201 outcome=success '
            'completion_phase=handler duration_ms=512.126995')

    def test_actual_fs_line_has_exact_trace_and_identity(self):
        fields = debug.attr_fields(self.line, {})
        self.assertEqual(fields.get("trace_id"), self.trace)
        self.assertEqual([fields[k] for k in ("cluster", "tenant_id", "instance_id", "branch_id")],
                         ["dev", "tenant", "sqlite-fixture", "main"])
        for parent in ("x" + self.parent, self.parent + "extra",
                       self.parent.replace("7ca0d5adb83860b9", "0" * 16),
                       self.parent.replace(self.trace, "0" * 32)):
            self.assertFalse(debug.attr_fields(self.line.replace(self.parent, parent), {}).get("trace_id"))
        conflict = debug.attr_fields(self.line + ' trace_id="' + "1" * 32 + '"', {})
        self.assertEqual(conflict["trace_id"], "1" * 32)

    def test_trace_search_queries_parent_and_rejects_other_trace(self):
        owner = self
        class Backend:
            def get(self, backend, path, params):
                query = params["query"]
                if "traceparent" not in query:
                    return {"status": "success", "data": {"result": []}}
                return {"status": "success", "data": {"result": [{"stream": {}, "values": [
                    ["1", owner.line], ["2", owner.line.replace(owner.trace, "1" * 32)],
                    ["3", owner.line.replace(owner.parent, owner.parent + "extra")],
                ]}]}}
        now = datetime(2026, 9, 27, tzinfo=timezone.utc)
        gaps = []
        logs = debug.search_logs(Backend(), "dev", "trace_id", self.trace, now, now + timedelta(seconds=1), gaps)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["fields"]["component"], "fs")
        self.assertEqual(gaps, [])
        for parser in ("", "json", "logfmt"):
            query = debug.log_query("dev", "trace_id", self.trace, "fs", "dev", parser)
            self.assertIn("traceparent", query)
            self.assertIn("^00-" + self.trace, query)
            self.assertIn("$", query)


if __name__ == "__main__":
    unittest.main()
