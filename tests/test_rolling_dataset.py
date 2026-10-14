import unittest
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal

from src.logistics.experiments import RunPolicy, run_experiment
from src.logistics.rolling import build_rolling_dataset
from src.logistics.scenarios import ScenarioConfig
from tests.test_estimates import request
from tests.test_recovery import fixture


def result(stock=20):
    w = fixture()
    if stock:
        w.receive("stock", 0, "origin", {"a": stock})
    return run_experiment(
        ScenarioConfig(generation_days=1, extension_days=0),
        RunPolicy(observation_interval_s=600),
        warehouse=w,
        requests=[replace(request(), deadline_margin=Decimal(".5"))],
    )


class RollingDatasetTests(unittest.TestCase):
    def test_separate_targets_and_unit_mission_weight(self):
        data = build_rolling_dataset(result())
        targets = data["targets"]
        self.assertEqual(
            [t["target_kind"] for t in targets],
            ["delay_if_late", "remaining_after_deadline", "remaining_after_deadline"],
        )
        self.assertEqual([t["target_minutes"] for t in targets], [20, 20, 10])
        self.assertAlmostEqual(sum(t["sample_weight"] for t in targets), 1)
        self.assertTrue(all("late" not in r["features"] for r in data["observations"]))

    def test_incomplete_targets_remain_null(self):
        data = build_rolling_dataset(result(0))
        self.assertTrue(all(t["target_minutes"] is None for t in data["targets"]))
        self.assertTrue(all(t["quota_censored"] for t in data["targets"]))
        self.assertAlmostEqual(sum(t["sample_weight"] for t in data["targets"]), 1)

    def test_exact_duplicates_do_not_change_weight(self):
        r = result()
        r["rolling_observations"].append(deepcopy(r["rolling_observations"][0]))
        data = build_rolling_dataset(r)
        self.assertEqual(len(data["observations"]), 3)
        self.assertAlmostEqual(sum(t["sample_weight"] for t in data["targets"]), 1)
        r["rolling_observations"][-1]["features"]["status"] = "changed"
        with self.assertRaises(ValueError):
            build_rolling_dataset(r)

    def test_unknown_features_or_temporal_mismatch_block_build(self):
        for mutation in (
            lambda row: row["features"].update(hidden_bad=2),
            lambda row: row.update(observed_s=999999),
            lambda row: row["features"].update(elapsed_s=0),
            lambda row: row["features"]["lines"].clear(),
        ):
            r = result()
            mutation(r["rolling_observations"][0])
            with self.assertRaises(ValueError):
                build_rolling_dataset(r)


if __name__ == "__main__":
    unittest.main()
