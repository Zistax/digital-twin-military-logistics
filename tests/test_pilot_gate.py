import unittest
from copy import deepcopy

from src.logistics.pilot_gate import evaluate_pilot


def records():
    return [
        {
            "seed": seed,
            "profile": profile,
            "valid": True,
            "unexplained_open_missions": [],
            "trace_rows": 336,
            "trace_sha256": "present",
            "wall_seconds": 100,
            "kpi": {
                "quota_reached": 9,
                "quota_censored": 1,
                "cancelled": 0,
                "missions": 10,
                "on_time_reached": 3,
                "known_late": 7,
            },
        }
        for seed in (0, 1, 2)
        for profile in ("regular", "pressure", "perturbed")
    ]


class PilotGateTests(unittest.TestCase):
    def test_complete_pilot_does_not_clear_unfinished_project_gates(self):
        result = evaluate_pilot(records())
        self.assertTrue(result["passed"])
        self.assertFalse(result["ready_for_D03"])

    def test_missing_invalid_unexplained_or_slow_run_blocks_acceptance(self):
        for mutation in (
            lambda rows: rows.pop(),
            lambda rows: rows[0].update(valid=False),
            lambda rows: rows[0].update(unexplained_open_missions=["m"]),
            lambda rows: rows[0].update(wall_seconds=601),
            lambda rows: rows[0].update(trace_rows=0),
        ):
            rows = deepcopy(records())
            mutation(rows)
            self.assertFalse(evaluate_pilot(rows)["passed"])

    def test_uniform_timing_outcomes_require_more_pilot_evidence(self):
        rows = records()
        for row in rows:
            row["kpi"]["on_time_reached"] = 0
        self.assertFalse(evaluate_pilot(rows)["passed"])


if __name__ == "__main__":
    unittest.main()
