import unittest
from decimal import Decimal as D

from src.logistics.core import Mission, MissionLine
from src.logistics.pilot_checks import operational_checkpoint, explain_open_mission
from tests.test_recovery import fixture, prepare
from src.logistics.warehouse import Item


class PilotAcceptanceTests(unittest.TestCase):
    def test_urgent_reinforcement_skips_donor_without_requested_item(self):
        w = fixture(items=[Item("a", D(1), D(1), 30), Item("b", D(1), D(1), 30)])
        w.receive("stock", 0, "origin", {"a": 10})
        w.register(
            "urgent",
            0,
            Mission(
                "run", "m", "origin", "dest", 0, 2500, (MissionLine("a", 10, D(".9")),)
            ),
            urgent=True,
        )
        w.schedule("schedule", 0, "m")
        w.advance("travel", 1000)
        w.damage_cargo("damage", 1000, "auto-1-0", "a", 2)
        w.advance("inspect", 2400)
        w.register(
            "donor",
            2400,
            Mission(
                "run",
                "donor",
                "origin",
                "dest",
                2400,
                8000,
                (MissionLine("b", 1, D(1)),),
            ),
        )
        w.decide("approve", 2400, "request-1", "approve")
        w.advance("wait", 2500)
        self.assertEqual(w._requests["request-1"]["waiting_reason"], "stock")
        self.assertNotIn("a", w._jobs["donor"].reserved)
        w.receive("more-stock", 2500, "origin", {"a": 1})
        w.advance("done", 6000)
        self.assertEqual(w.outcome("m", 6000).accepted["a"], 9)

    def test_finite_internal_queue_does_not_leave_supplier_permanently_blocked(self):
        w = fixture()
        w.receive("stock", 0, "origin", {"a": 20})
        for mid in ("one", "two"):
            w.register(
                "register:" + mid,
                0,
                Mission(
                    "run",
                    mid,
                    "origin",
                    "dest",
                    0,
                    10000,
                    (MissionLine("a", 10, D(1)),),
                ),
            )
            w.schedule("schedule:" + mid, 0, mid)
        w.order_supply("supply", 0, "s", "origin", {"a": 10}, 100)
        w.advance("done", 5000)
        supply = w.observed_supplies()["s"]
        self.assertEqual(supply["status"], "closed")
        self.assertEqual(supply["received"], {"a": 10})
        self.assertEqual(w._supply_wait["s"]["berth"], 1100)
        self.assertTrue(
            all(w.outcome(mid, 5000).logistics_complete for mid in ("one", "two"))
        )

    def test_stock_fleet_and_queue_blockers_are_distinguishable(self):
        w = fixture()
        w.register(
            "mission",
            0,
            Mission(
                "run", "m", "origin", "dest", 0, 10000, (MissionLine("a", 10, D(1)),)
            ),
        )
        w.schedule("schedule", 0, "m")
        w.advance("stock-wait", 100)
        self.assertEqual(explain_open_mission(w, "m", 100)[0]["kind"], "stock")
        w.receive("stock", 100, "origin", {"a": 10})
        w.reserve("reserve", 100, "m")
        w._busy = {"v0": "other-one", "v1": "other-two"}
        self.assertEqual(explain_open_mission(w, "m", 100)[0]["kind"], "fleet_or_route")

    def test_checkpoint_is_detached_and_hides_future_supplier_outcome(self):
        w = fixture()
        w.order_supply("supply", 0, "s", "origin", {"a": 10}, 100, 9000, {"a": 3})
        w.advance("begin", 0)
        checkpoint = operational_checkpoint(w, 0)
        self.assertNotIn("actual_s", checkpoint["supplies"]["s"])
        self.assertNotIn("remaining", checkpoint["supplies"]["s"])
        checkpoint["stock"]["origin"]["a"] = 999
        self.assertNotEqual(w._stock["origin"].get("a"), 999)

    def test_moving_and_broken_vehicles_explain_open_missions(self):
        w = fixture()
        prepare(w)
        self.assertEqual(explain_open_mission(w, "m", 1000)[0]["kind"], "loaded_travel")
        w.breakdown("broken", 1000, "v0", duration_s=900)
        self.assertEqual(
            explain_open_mission(w, "m", 1000)[0]["kind"], "broken_vehicle"
        )


if __name__ == "__main__":
    unittest.main()
