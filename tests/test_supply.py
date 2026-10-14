import unittest
from datetime import datetime, timezone
from decimal import Decimal as D

from src.logistics.calendars import Calendar
from src.logistics.core import Mission, MissionLine
from src.logistics.operations import DepotOperations
from src.logistics.roads import Network, Node, Road
from src.logistics.supply import ReorderRule, SupplyWarehouse
from src.logistics.warehouse import Item, Store, Vehicle


def build(capacity=100, calendar=None):
    return SupplyWarehouse(
        "run",
        [Item("a", D(1), D(1), 30)],
        [Store("origin", D(capacity), D(0)), Store("dest", D(100), D(0))],
        [Vehicle("v", "origin", D(100), D(100))],
        network=Network(
            [Node("origin", 0, 0), Node("dest", 1, 0)],
            [Road("origin", "dest", 30)],
            congestion_alpha=0,
        ),
        epoch=datetime(2026, 10, 5, 6, tzinfo=timezone.utc),
        operations={
            d: DepotOperations(calendar or Calendar.daily()) for d in ("origin", "dest")
        },
    )


def mission(w, mid="m", urgent=False):
    w.register(
        "register-" + mid,
        0,
        Mission("run", mid, "origin", "dest", 0, 6000, (MissionLine("a", 10, D(1)),)),
        urgent,
    )
    w.schedule("schedule-" + mid, 0, mid)


class SupplyTests(unittest.TestCase):
    def test_only_unloaded_goods_available(self):
        w = build()
        w.order_supply("o", 0, "s", "origin", {"a": 10}, 100)
        w.advance("arrival", 100)
        self.assertEqual(w.available("origin", "a"), 0)
        w.advance("done", 700)
        self.assertEqual(w.available("origin", "a"), 10)
        self.assertEqual(w.snapshot()["supplies"]["s"]["status"], "closed")

    def test_partial_supply_closes_missing_balance(self):
        w = build()
        w.order_supply(
            "o",
            0,
            "s",
            "origin",
            {"a": 10},
            100,
            actual_s=200,
            actual_quantities={"a": 6},
        )
        self.assertEqual(w.inventory_position("origin", "a"), 10)
        w.advance("arrive", 200)
        self.assertEqual(w.inventory_position("origin", "a"), 6)
        w.advance("done", 800)
        self.assertEqual(w.snapshot()["supplies"]["s"]["not_delivered"], {"a": 4})
        self.assertEqual(w.snapshot()["supplies"]["s"]["status"], "closed")

    def test_closed_depot_waits(self):
        w = build(calendar=Calendar.daily(10 * 3600, 18 * 3600))
        w.order_supply("o", 0, "s", "origin", {"a": 10}, 100)
        w.advance("before", 7199)
        self.assertFalse(w.snapshot()["active"])
        w.advance("done", 7800)
        self.assertEqual(w.available("origin", "a"), 10)

    def test_partial_unload_and_local_consumption_unblock(self):
        w = build(capacity=5)
        w.order_supply("o", 0, "s", "origin", {"a": 10}, 0)
        w.local_request("r", 0, "local", "origin", {"a": 10})
        w.advance("done", 1200)
        self.assertEqual(w.snapshot()["consumed"]["a"], 10)
        self.assertEqual(w.snapshot()["supplies"]["s"]["status"], "closed")
        self.assertEqual(w.available("origin", "a"), 0)
        self.assertEqual(len(w.snapshot()["local_requests"]["local"]["withdrawals"]), 2)

    def test_existing_reserves_protected_from_local(self):
        w = build()
        w.receive("stock", 0, "origin", {"a": 10})
        mission(w)
        w.reserve("reserve", 0, "m")
        w.local_request("local", 0, "r", "origin", {"a": 5})
        w.advance("go", 0)
        self.assertEqual(w.snapshot()["local_requests"]["r"]["remaining"], {"a": 5})

    def test_new_goods_priority_urgent_local_ordinary(self):
        w = build()
        mission(w, "normal")
        mission(w, "urgent", True)
        w.local_request("local", 0, "r", "origin", {"a": 5})
        w.order_supply("supply", 0, "s", "origin", {"a": 20}, 0)
        w.advance("unloaded", 900)
        self.assertEqual(w.snapshot()["consumed"]["a"], 5)
        self.assertEqual(w.snapshot()["jobs"]["normal"].reserved["a"], 5)
        self.assertEqual(w.snapshot()["jobs"]["urgent"].reserved["a"], 10)

    def test_fifo_local_backlogs(self):
        w = build()
        w.local_request("first", 0, "a", "origin", {"a": 6}, 1)
        w.local_request("second", 0, "b", "origin", {"a": 6}, 2)
        w.receive("stock", 0, "origin", {"a": 8})
        w.advance("consume", 2)
        self.assertEqual(w.snapshot()["local_requests"]["a"]["remaining"], {"a": 0})
        self.assertEqual(w.snapshot()["local_requests"]["b"]["remaining"], {"a": 4})

    def test_reorder_no_duplicate_with_open_order(self):
        w = build()
        rule = ReorderRule(D(10), D("0.5"), D(1), 1000)
        w.configure_reorder("config", 0, {("origin", "a"): rule}, 100)
        w.advance("repeat", 900)
        self.assertEqual(len(w.snapshot()["supplies"]), 1)
        self.assertEqual(w.inventory_position("origin", "a"), 10)

    def test_programmed_supply_prevents_duplicate(self):
        w = build()
        w.order_supply("o", 0, "scheduled", "origin", {"a": 10}, 1000)
        w.configure_reorder(
            "c", 0, {("origin", "a"): ReorderRule(D(10), D("0.5"), D(1), 1000)}
        )
        w.advance("go", 0)
        self.assertEqual(len(w.snapshot()["supplies"]), 1)

    def test_no_double_counting_reservations(self):
        w = build()
        w.receive("stock", 0, "origin", {"a": 10})
        mission(w)
        w.reserve("r", 0, "m")
        self.assertEqual(w.inventory_position("origin", "a"), 0)
        w.local_request("local", 0, "l", "origin", {"a": 3})
        self.assertEqual(w.inventory_position("origin", "a"), -3)

    def test_zero_demand_and_capacity_limit(self):
        w = build(capacity=5)
        w.configure_reorder(
            "c", 0, {("origin", "a"): ReorderRule(D(10), D("0.5"), D(1), 1000)}
        )
        w.advance("go", 0)
        self.assertEqual(w.snapshot()["supplies"]["reorder-1"]["ordered"], {"a": 5})
        z = build()
        z.configure_reorder(
            "c", 0, {("origin", "a"): ReorderRule(D(0), D("0.5"), D(1), 1000)}
        )
        z.advance("go", 10000)
        self.assertFalse(z.snapshot()["supplies"])

    def test_daily_generation_is_seeded_and_weekend_backlog(self):
        def generated():
            w = build(calendar=Calendar.daily(8 * 3600, 17 * 3600, range(5)))
            w.schedule_local_days("daily", 0, "origin", {"a": D(10)}, 7, 42)
            return w

        a, b = generated(), generated()
        self.assertEqual(a.snapshot()["local_requests"], b.snapshot()["local_requests"])
        self.assertEqual(len(a.snapshot()["local_requests"]), 7)
        a.receive("stock", 0, "origin", {"a": 100})
        a.advance("sunday", 6 * 86400)
        weekend = [
            r
            for r in a.snapshot()["local_requests"].values()
            if r["due_s"] >= 5 * 86400
        ]
        self.assertTrue(all(r["completed_s"] is None for r in weekend))
        a.advance("monday", 7 * 86400)
        self.assertTrue(
            all(
                r["completed_s"] is not None
                for r in a.snapshot()["local_requests"].values()
            )
        )

    def test_receipt_drives_whole_mission(self):
        w = build()
        mission(w)
        w.order_supply("s", 0, "s", "origin", {"a": 10}, 0)
        w.advance("done", 1920)
        self.assertTrue(w.outcome("m", 1920).logistics_complete)
        self.assertEqual(w.snapshot()["stock"]["dest"]["a"], 10)

    def test_future_actual_quantities_do_not_change_inventory_position(self):
        a, b = build(), build()
        for w, actual in ((a, 10), (b, 2)):
            w.order_supply(
                "o",
                0,
                "s",
                "origin",
                {"a": 10},
                100,
                actual_s=200,
                actual_quantities={"a": actual},
            )
            w.advance("before", 199)
        self.assertEqual(
            a.inventory_position("origin", "a"), b.inventory_position("origin", "a")
        )

    def test_partial_arrival_triggers_only_missing_reorder(self):
        w = build()
        w.order_supply(
            "o", 0, "s", "origin", {"a": 10}, 100, actual_quantities={"a": 2}
        )
        w.configure_reorder(
            "c", 0, {("origin", "a"): ReorderRule(D(10), D("0.5"), D(1), 1000)}, 100
        )
        w.advance("partial", 100)
        self.assertEqual(w.snapshot()["supplies"]["reorder-1"]["ordered"], {"a": 8})
        w.advance("repeat", 200)
        self.assertEqual(len(w.snapshot()["supplies"]), 2)

    def test_external_and_fleet_operations_coexist(self):
        w = build()
        w.receive("stock", 0, "origin", {"a": 10})
        mission(w)
        w.order_supply("o", 0, "external", "dest", {"a": 5}, 0)
        w.advance("start", 0)
        self.assertEqual(len(w.snapshot()["active"]), 2)
        w.advance("done", 1320)
        self.assertTrue(w.outcome("m", 1320).logistics_complete)
        self.assertEqual(w.snapshot()["stock"]["dest"]["a"], 15)

    def test_demo_repeatable_and_balanced(self):
        from src.logistics.supply_demo import run_demo

        result = run_demo()
        self.assertEqual(result, run_demo())
        self.assertTrue(result["outcome"]["logistics_complete"])
        self.assertEqual(len(result["supplies"]), 1)
        self.assertEqual(result["supplies"]["reorder-1"]["ordered"], {"goods": 25})
        self.assertEqual(result["consumed"]["goods"], 5)
        self.assertEqual(result["stock"]["local"]["goods"], 10)
        self.assertEqual(result["stock"]["destination"]["goods"], 10)

    def test_idempotency_and_invalid_supply(self):
        w = build()
        w.order_supply("o", 0, "s", "origin", {"a": 10}, 0)
        before = w.snapshot()
        w.order_supply("o", 0, "s", "origin", {"a": 10}, 0)
        self.assertEqual(before, w.snapshot())
        with self.assertRaises(ValueError):
            w.order_supply(
                "bad", 0, "bad", "origin", {"a": 10}, 0, actual_quantities={"a": 11}
            )
        self.assertEqual(before, w.snapshot())


if __name__ == "__main__":
    unittest.main()
