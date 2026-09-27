"""Replay sanitized collected Directory cache timeouts with a successful request."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import tiana_debug as debug


class DirectoryDegradationTests(unittest.TestCase):
    def records(self):
        records = json.loads((Path(__file__).parent / "fixtures/directory_redis_degraded.json").read_text())
        for record in records:
            record["fields"] = debug.attr_fields(record["line"], record["stream"])
        return records

    def test_collected_cache_timeouts_are_degradation_not_request_failure(self):
        records = self.records()
        diagnosis = debug.failure_evidence(records, "req-directory-degraded")
        self.assertEqual(diagnosis["failure_component"], "")
        self.assertIsNone(diagnosis["root_cause_evidence"])
        self.assertIsNone(diagnosis["candidate_failure"])
        events = diagnosis["dependency_degradations"]
        self.assertEqual({e["operation"] for e in events}, {"get_cluster", "put_cluster"})
        self.assertTrue(all(e["reason"].endswith("i/o timeout") and e["component"] == "directory"
                            and e["dependency"] == "redis" for e in events))
        self.assertEqual(records[-1]["fields"]["status"], 200)
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            debug.evidence_files(root, {"environment": "test", "identity": "req-directory-degraded",
                "status": "complete", "window": {"start": "start", "end": "end"},
                "diagnosis": diagnosis, "gaps": []}, records, {})
            report = (root / "diagnosis.md").read_text()
            self.assertIn("Directory Redis dependency degradation", report)
            self.assertIn("get_cluster", report)
            self.assertIn("put_cluster", report)
            self.assertIn("i/o timeout", report)
            self.assertIn("HTTP 200", report)
            self.assertNotIn("Direct failure event", report)

    def test_exact_event_component_and_dependency_required(self):
        for key, value in (("event", "other.degraded"), ("component", "control"),
                           ("dependency", "mysql")):
            records = self.records()
            for record in records[:-1]:
                record["fields"][key] = value
            self.assertEqual(debug.failure_evidence(records)["dependency_degradations"], [])

    def test_actual_failure_stays_separate(self):
        records = self.records()
        records.append({"time_unix_nano": "1790508808383425565", "stream": {},
            "fields": {"component": "directory", "event": "request.failed",
                       "reason": "database unavailable", "status": 500}})
        diagnosis = debug.failure_evidence(records)
        self.assertEqual(diagnosis["root_cause_evidence"]["reason"], "database unavailable")
        self.assertEqual(len(diagnosis["dependency_degradations"]), 2)
