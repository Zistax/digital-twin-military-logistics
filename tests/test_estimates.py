import unittest
from dataclasses import replace
from decimal import Decimal as D

from src.logistics.core import MissionLine
from src.logistics.estimates import estimate_request, mission_from_estimate
from src.logistics.scenarios import ScenarioRequest
from tests.test_recovery import fixture


def request(at_s=0):
    return ScenarioRequest(
        "new",
        at_s,
        "origin",
        "dest",
        False,
        (MissionLine("a", 10, D(".9")),),
        "ordinary",
        D("1.5"),
    )


class EstimateTests(unittest.TestCase):
    def test_free_fleet_estimate_and_deadline(self):
        w = fixture()
        w.receive("stock", 0, "origin", {"a": 20})
        before = w.snapshot()
        estimate = estimate_request(w, request())
        self.assertEqual(estimate.duration_s, 2400)
        self.assertEqual(
            mission_from_estimate("run", request(), estimate).deadline_s, 3600
        )
        self.assertEqual(w.snapshot(), before)

    def test_hidden_supplier_outcome_does_not_change_estimate(self):
        a, b = fixture(), fixture()
        a.order_supply("s", 0, "order", "origin", {"a": 10}, 1000, 2000, {"a": 3})
        b.order_supply("s", 0, "order", "origin", {"a": 10}, 1000, 9000, {"a": 8})
        self.assertEqual(estimate_request(a, request()), estimate_request(b, request()))
        self.assertEqual(estimate_request(a, request()).duration_s, 4000)

    def test_unknown_stock_and_busy_fleet_are_explicit(self):
        w = fixture()
        w.advance("begin", 0)
        estimate = estimate_request(w, request())
        self.assertIsNone(estimate.duration_s)
        with self.assertRaises(ValueError):
            mission_from_estimate("run", request(), estimate)
        w.receive("stock", 0, "origin", {"a": 20})
        w._busy = {"v0": "trip-a", "v1": "trip-b"}
        self.assertEqual(
            estimate_request(w, request()).reason, "insufficient_free_compatible_fleet"
        )

    def test_calendar_and_current_road_conditions_affect_estimate(self):
        from src.logistics.calendars import Calendar

        w = fixture()
        w.receive("stock", 0, "origin", {"a": 20})
        w._operations["origin"] = replace(
            w._operations["origin"], calendar=Calendar.daily(6 * 3600, 22 * 3600)
        )
        estimate = estimate_request(w, request())
        self.assertEqual(estimate.duration_s, 4 * 3600 + 2400)  # epoch is 02:00 local
        w.road_condition("traffic", 0, "origin", "dest", traffic=2)
        self.assertEqual(
            estimate_request(w, request()).duration_s, estimate.duration_s + 1200
        )

    def test_overdue_supply_and_unadvanced_time_are_not_guessed(self):
        w = fixture()
        w.order_supply("s", 0, "order", "origin", {"a": 10}, 1000, 9000)
        with self.assertRaises(ValueError):
            estimate_request(w, request(1000))
        w.advance("now", 1000)
        self.assertIsNone(estimate_request(w, request(1000)).duration_s)


if __name__ == "__main__":
    unittest.main()
