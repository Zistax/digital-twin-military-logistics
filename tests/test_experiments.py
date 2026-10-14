import unittest

from src.logistics.experiments import RunPolicy, run_experiment
from src.logistics.scenarios import ScenarioConfig
from tests.test_estimates import request
from tests.test_recovery import fixture


class ExperimentTests(unittest.TestCase):
    def test_completion_exactly_at_limit_is_not_censored(self):
        w = fixture()
        w.receive("stock", 0, "origin", {"a": 20})
        result = run_experiment(
            ScenarioConfig(generation_days=1, extension_days=0),
            warehouse=w,
            requests=[request(84000)],
        )
        self.assertEqual(result["outcomes"]["new"]["quota_reached_s"], 86400)
        self.assertFalse(result["outcomes"]["new"]["quota_censored"])
        self.assertEqual(result["stop_reason"], "missions_drained")

    def test_complete_and_reproducible(self):
        def run():
            w = fixture()
            w.receive("stock", 0, "origin", {"a": 20})
            return run_experiment(ScenarioConfig(), warehouse=w, requests=[request()])

        result = run()
        self.assertEqual(result, run())
        self.assertEqual(result["stop_reason"], "missions_drained")
        self.assertEqual(result["stopped_s"], 7 * 86400)
        self.assertEqual(result["outcomes"]["new"]["quota_reached_s"], 2400)
        self.assertFalse(result["outcomes"]["new"]["quota_censored"])

    def test_unavailable_estimate_preserves_start_and_marks_allowance(self):
        result = run_experiment(
            ScenarioConfig(generation_days=1, extension_days=0),
            RunPolicy(unavailable_allowance_s=1000),
            warehouse=fixture(),
            requests=[request(100)],
        )
        creation = result["creations"][0]
        self.assertIsNone(creation["estimate"]["duration_s"])
        self.assertEqual(creation["deadline_source"], "configured_allowance")
        self.assertEqual(creation["deadline_s"], 1600)
        outcome = result["outcomes"]["new"]
        self.assertTrue(outcome["quota_censored"])
        self.assertIsNone(outcome["delay_minutes"])
        self.assertEqual(result["stop_reason"], "time_limit")

    def test_additional_period_allows_late_completion(self):
        w = fixture()
        w.receive("stock", 0, "origin", {"a": 20})
        result = run_experiment(
            ScenarioConfig(generation_days=1, extension_days=1),
            warehouse=w,
            requests=[request(86000)],
        )
        self.assertEqual(result["stop_reason"], "missions_drained")
        self.assertGreater(result["stopped_s"], 86400)
        self.assertLess(result["stopped_s"], 172800)

    def test_background_supply_does_not_prevent_stop(self):
        w = fixture()
        w.order_supply("background", 0, "s", "origin", {"a": 10}, 200000)
        result = run_experiment(
            ScenarioConfig(generation_days=1), warehouse=w, requests=[]
        )
        self.assertEqual(result["stopped_s"], 86400)
        self.assertEqual(w.observed_supplies()["s"]["status"], "expected")

    def test_invalid_requests_rejected_before_execution(self):
        for requests in (
            [request(), request()],
            [request(86400)],
            [request(10), request()],
        ):
            with self.assertRaises(ValueError):
                run_experiment(
                    ScenarioConfig(generation_days=1),
                    warehouse=fixture(),
                    requests=requests,
                )
        with self.assertRaises(ValueError):
            RunPolicy(completion_check_s=0)


if __name__ == "__main__":
    unittest.main()
