import unittest
from decimal import Decimal as D

from src.logistics.incidents import IncidentPolicy
from src.logistics.supply import ReorderRule
from tests.test_recovery import fixture


def configured(profile="perturbed", automatic=True):
    w = fixture(policy=IncidentPolicy(seed=30, profile=profile, automatic=automatic))
    w.configure_reorder(
        "rules", 0, {("origin", "a"): ReorderRule(D(10), D(1), D(2), 3600)}
    )
    w.advance("begin", 0)
    return w


class ScenarioSupplyTests(unittest.TestCase):
    def test_automatic_reorder_samples_delay_and_shortfall(self):
        w = configured()
        supply = w.snapshot()["supplies"]["reorder-1"]
        self.assertEqual(supply["ordered"], {"a": 20})
        self.assertEqual(supply["expected_s"], 3600)
        self.assertEqual(supply["actual_s"], 51000)
        self.assertEqual(supply["actual"], {"a": 17})
        w.advance("overdue", 50000)
        self.assertEqual(len(w.observed_supplies()), 1)
        self.assertEqual(w.inventory_position("origin", "a"), 20)

    def test_observed_view_reveals_actual_only_after_arrival(self):
        w = configured()
        before = w.observed_supplies()["reorder-1"]
        for field in ("actual", "actual_s", "arrived_s", "not_delivered", "remaining"):
            self.assertNotIn(field, before)
        w.advance("arrival", 51000)
        after = w.observed_supplies()["reorder-1"]
        self.assertEqual(after["arrived_s"], 51000)
        self.assertEqual(after["not_delivered"], {"a": 3})
        self.assertEqual(after["remaining"], {"a": 17})
        self.assertEqual(w.inventory_position("origin", "a"), 17)
        after["remaining"]["a"] = 0
        self.assertEqual(w.observed_supplies()["reorder-1"]["remaining"]["a"], 17)

    def test_partition_invariance_through_arrival_and_inspection(self):
        a, b = configured(), configured()
        a.advance("all", 54000)
        for t in (3600, 10000, 50000, 51000, 52000, 54000):
            b.advance("part" + str(t), t)
        self.assertEqual(a.observed_supplies(), b.observed_supplies())
        self.assertEqual(a.snapshot()["stock"], b.snapshot()["stock"])
        supply = a.observed_supplies()["reorder-1"]
        self.assertEqual(supply["status"], "closed")
        self.assertEqual(supply["received"]["a"], 17)
        a._check()

    def test_deterministic_mode_and_pressure_pairing(self):
        w = configured(automatic=False)
        supply = w.snapshot()["supplies"]["reorder-1"]
        self.assertEqual(supply["actual_s"], supply["expected_s"])
        self.assertEqual(supply["actual"], supply["ordered"])
        a, b = configured("regular"), configured("pressure")
        self.assertEqual(a.snapshot()["supplies"], b.snapshot()["supplies"])


if __name__ == "__main__":
    unittest.main()
