import unittest
from copy import deepcopy

from src.logistics.environment import Conditions
from src.logistics.roads import reference_network
from src.logistics.scenarios import ScenarioConfig, initialize_scenario


class EnvironmentTests(unittest.TestCase):
    def test_partition_invariant_and_regular_pressure_equal(self):
        network = reference_network(4)
        a, b = Conditions(4, "regular", network), Conditions(4, "pressure", network)
        a.advance(86400)
        for t in (500, 1800, 4000, 20000, 86400):
            b.advance(t)
        self.assertEqual(a.history, b.history)
        self.assertEqual(a.forecasts, b.forecasts)

    def test_conditions_persist_and_stay_in_bounds(self):
        for profile, lo, hi, wlo, whi in (
            ("regular", 1, 1.4, 1.1, 1.3),
            ("perturbed", 1.2, 2, 1.2, 1.5),
        ):
            c = Conditions(5, profile, reference_network(5))
            c.advance(0)
            current = c.observed()
            c.advance(1799)
            self.assertEqual(c.observed()["traffic"], current["traffic"])
            c.advance(14 * 86400)
            self.assertTrue(any(h["weather"] > 1 for h in c.history))
            for h in c.history:
                self.assertTrue(all(lo <= v <= hi for v in h["traffic"].values()))
                self.assertTrue(h["weather"] == 1 or wlo <= h["weather"] <= whi)

    def test_forecast_has_no_access_to_true_future(self):
        a = Conditions(7, "perturbed", reference_network(7))
        a.advance(0)
        b = deepcopy(a)
        a._weather_end, b._weather_end = 3600, 20000
        # Forecast depends on observed weather and its own RNG only.
        self.assertEqual(a._forecast(3600, 1.3), b._forecast(3600, 1.3))
        observed = a.observed()
        self.assertNotIn("_weather_end", observed)
        forecast = observed["forecast"]
        self.assertEqual(len(forecast["values"]), 6)
        self.assertEqual(forecast["values"][-1]["valid_to_s"], 21600)
        observed["traffic"].clear()
        self.assertTrue(a.observed()["traffic"])

    def test_initialized_engine_applies_groups_and_versions(self):
        w, _ = initialize_scenario(ScenarioConfig(seed=3))
        w.advance("conditions", 3600)
        view = w.observed_environment()
        self.assertEqual(view["forecast"]["version"], 2)
        for edge, group in w._environment.groups.items():
            self.assertEqual(
                w._network.conditions[edge]["traffic"], view["traffic"][group]
            )
            self.assertEqual(w._network.conditions[edge]["weather"], view["weather"])


if __name__ == "__main__":
    unittest.main()
