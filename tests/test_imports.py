import json
import unittest
from copy import deepcopy
from datetime import datetime, timezone

from src.logistics.imports import import_observations
from tests.test_dataset import run


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.row = run()["observations"][0]
        self.options = dict(
            missions={("run", "new"): {"start_s": 0, "deadline_s": 3600}},
            epoch=datetime(2026, 10, 5, tzinfo=timezone.utc),
            cutoff_s=86400,
        )

    def load(self, rows):
        return import_observations("\n".join(rows), **self.options)

    def test_roundtrip_and_exact_retry(self):
        line = json.dumps(self.row)
        result = self.load([line, line])
        self.assertFalse(result["blocked"])
        self.assertEqual(result["records"], [self.row])
        self.assertEqual(result["exact_duplicates"], 1)

    def test_exact_threshold_and_over_threshold(self):
        line = json.dumps(self.row)
        at = self.load([line] * 199 + ["broken"])
        self.assertFalse(at["blocked"])
        self.assertEqual(at["invalid_rows"], 1)
        above = self.load([line] * 198 + ["broken"])
        self.assertTrue(above["blocked"])
        self.assertEqual(above["records"], [])

    def test_critical_orphan_blocks_even_under_threshold(self):
        orphan = deepcopy(self.row)
        orphan["mission_id"] = "missing"
        orphan["observation_id"] = "missing:creation"
        result = self.load([json.dumps(self.row)] * 300 + [json.dumps(orphan)])
        self.assertTrue(result["blocked"])
        self.assertFalse(result["threshold_exceeded"])

    def test_hidden_feature_is_critical_under_threshold(self):
        row = deepcopy(self.row)
        row["features"]["actual_future_arrival"] = 1000
        result = self.load([json.dumps(self.row)] * 300 + [json.dumps(row)])
        self.assertTrue(result["blocked"])
        self.assertTrue(result["critical"])

    def test_future_cutoff_is_critical_even_when_schema_invalid(self):
        row = deepcopy(self.row)
        row["observed_s"] = 86401
        result = self.load([json.dumps(self.row)] * 300 + [json.dumps(row)])
        self.assertTrue(result["blocked"])
        self.assertFalse(result["threshold_exceeded"])
        self.assertTrue(result["critical"])

    def test_conflicts_and_temporal_mismatch(self):
        for field, value in (
            ("observation_id", "second"),
            ("observed_utc", "2026-10-06T00:00:00+00:00"),
        ):
            row = deepcopy(self.row)
            row[field] = value
            self.assertTrue(
                self.load([json.dumps(self.row), json.dumps(row)])["blocked"]
            )
        row = deepcopy(self.row)
        row["features"]["free_vehicles"] = 0
        result = self.load([json.dumps(self.row), json.dumps(row)])
        self.assertIn("conflicting", result["critical"][0]["reason"])

    def test_invalid_json_shapes_and_duplicate_keys_quarantined(self):
        for raw in ("null", "[]", '{"a":1,"a":2}', '{"a":NaN}', ""):
            result = self.load([raw, json.dumps(self.row)])
            self.assertTrue(result["blocked"])
            self.assertEqual(result["invalid_rows"], 1)


if __name__ == "__main__":
    unittest.main()
