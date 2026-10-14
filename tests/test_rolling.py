import unittest

from src.logistics.experiments import RunPolicy, run_experiment
from src.logistics.rolling import rolling_observations
from src.logistics.scenarios import ScenarioConfig
from tests.test_estimates import request
from tests.test_recovery import fixture, prepare


class RollingTests(unittest.TestCase):
    def test_hidden_damage_does_not_change_features(self):
        w = fixture()
        prepare(w)
        before = rolling_observations(w)
        w.damage_cargo("damage", 1000, "auto-1-0", "a", 2)
        self.assertEqual(before, rolling_observations(w))
        w.advance("inspect", 2400)
        line = rolling_observations(w)[0]["features"]["lines"][0]
        self.assertEqual(line["accepted"], 8)
        self.assertEqual(line["unusable_inspected"], 2)

    def test_runner_samples_live_and_stops_after_quota(self):
        w = fixture()
        w.receive("stock", 0, "origin", {"a": 20})
        result = run_experiment(
            ScenarioConfig(generation_days=1, extension_days=0),
            RunPolicy(observation_interval_s=600),
            warehouse=w,
            requests=[request()],
        )
        rows = result["rolling_observations"]
        self.assertEqual([r["observed_s"] for r in rows], [600, 1200, 1800])
        self.assertTrue(all(r["features"]["lines"][0]["accepted"] == 0 for r in rows))
        self.assertEqual(result["outcomes"]["new"]["accepted"]["a"], 10)

    def test_cancellation_excluded_and_records_detached(self):
        w = fixture()
        prepare(w)
        rows = rolling_observations(w)
        rows[0]["features"]["lines"][0]["reserved"] = 999
        self.assertNotEqual(
            rolling_observations(w)[0]["features"]["lines"][0]["reserved"], 999
        )
        w.cancel("cancel", 1000, "m")
        self.assertEqual(rolling_observations(w), [])


if __name__ == "__main__":
    unittest.main()
