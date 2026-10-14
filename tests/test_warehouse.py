"""Acceptance tests for stock -> reservation -> physical load -> mission replay."""

import unittest
from dataclasses import replace
from decimal import Decimal as D

from src.logistics.core import Delivery, Mission, MissionLine
from src.logistics.warehouse import Item, Store, Vehicle, Warehouse


def fixture():
    return Warehouse(
        "run",
        [
            Item("a", D(10), D("0.1"), 30),
            Item("b", D(20), D("0.2"), 120),
            Item("cold", D(5), D("0.1"), 30, True),
            Item("warm", D(5), D("0.1"), 30, False, False),
        ],
        [
            Store("origin", D(10), D(2)),
            Store("dest", D(10), D(2)),
            Store("dry", D(10), D(0)),
        ],
        [
            Vehicle("v1", "origin", D(100), D(2)),
            Vehicle("v2", "origin", D(200), D(2)),
            Vehicle("cold-v", "origin", D(100), D(2), True),
            Vehicle("remote-v", "dest", D(100), D(2)),
        ],
    )


def mission(mid="m", item="a", quantity=10, deadline=3600):
    return Mission(
        "run",
        mid,
        "origin",
        "dest",
        0,
        deadline,
        (MissionLine(item, quantity, D("0.9")),),
    )


class WarehouseTests(unittest.TestCase):
    def setUp(self):
        self.w = fixture()

    def prepare(self, quantity=10, urgent=False):
        self.w.receive("receipt", 0, "origin", {"a": quantity})
        self.w.register("register", 0, mission(), urgent)
        self.w.reserve("reserve", 0, "m")

    def rejected_unchanged(self, fn, *args):
        before = self.w.snapshot()
        with self.assertRaises(ValueError):
            fn(*args)
        self.assertEqual(before, self.w.snapshot())

    def test_reservation_is_not_extra_stock(self):
        self.prepare()
        self.assertEqual(self.w.available("origin", "a"), 0)
        self.assertEqual(self.w.snapshot()["stock"]["origin"]["a"], 10)
        self.w.reserve("again", 0, "m")
        self.assertEqual(self.w.snapshot()["jobs"]["m"].reserved["a"], 10)

    def test_ordinary_waits_urgent_minimum(self):
        self.prepare(9)
        self.assertFalse(self.w.ready("m"))
        self.rejected_unchanged(
            self.w.start_loading, "load", 0, "m", {"t": ("v1", {"a": 9})}
        )
        self.w.register("urgent", 0, mission("u"), True)
        result = self.w.reserve("steal", 0, "u")
        self.assertEqual(result["transfers"], [("m", "a", 9)])
        self.assertTrue(self.w.ready("u"))
        self.assertFalse(self.w.ready("m"))
        self.assertEqual(self.w.snapshot()["jobs"]["m"].mission.deadline_s, 3600)

    def test_each_item_required_for_urgent(self):
        self.w.receive("receipt", 0, "origin", {"a": 10, "b": 4})
        m = replace(
            mission(),
            lines=(MissionLine("a", 10, D("0.9")), MissionLine("b", 5, D("0.9"))),
        )
        self.w.register("register", 0, m, True)
        self.w.reserve("reserve", 0, "m")
        self.assertFalse(self.w.ready("m"))

    def test_preemption_protects_started_loading(self):
        self.prepare()
        self.w.start_loading("load", 0, "m", {"t": ("v1", {"a": 10})})
        self.w.register("urgent", 0, mission("u"), True)
        self.assertEqual(self.w.reserve("steal", 0, "u")["transfers"], [])
        self.assertFalse(self.w.ready("u"))
        self.rejected_unchanged(self.w.cancel, "cancel", 0, "m")

    def test_cancel_releases_reserves(self):
        self.prepare()
        self.assertEqual(self.w.cancel("cancel", 0, "m"), {"a": 10})
        self.assertEqual(self.w.available("origin", "a"), 10)
        self.assertFalse(self.w.ready("m"))

    def test_atomic_receipt_capacity(self):
        self.rejected_unchanged(self.w.receive, "r", 0, "origin", {"a": 1, "b": 51})
        self.rejected_unchanged(self.w.receive, "c", 0, "dry", {"cold": 1})
        self.w.receive("r", 0, "origin", {"a": 100})
        self.assertEqual(self.w.available("origin", "a"), 100)
        self.rejected_unchanged(self.w.receive, "extra", 0, "origin", {"a": 1})

    def test_receipts_are_idempotent_and_conflicts_rejected(self):
        self.w.receive("r", 0, "origin", {"a": 10})
        before = self.w.snapshot()
        self.w.receive("r", 0, "origin", {"a": 10})
        self.assertEqual(before, self.w.snapshot())
        self.rejected_unchanged(self.w.receive, "r", 0, "origin", {"a": 9})

    def test_vehicle_weight_volume_position_and_atomic_plan(self):
        self.prepare()
        for plan in [
            {"t": ("remote-v", {"a": 10})},
            {"t": ("v1", {"a": 5}), "t2": ("v1", {"a": 5})},
            {"t": ("v1", {"a": 11})},
            {"t": ("v1", {"a": 5})},
        ]:
            self.rejected_unchanged(self.w.start_loading, "bad", 0, "m", plan)
        # Independent volume bound, with enough weight capacity.
        w = Warehouse(
            "run",
            [Item("a", D(1), D(1), 30)],
            [Store("origin", D(20), D(0)), Store("dest", D(20), D(0))],
            [Vehicle("v", "origin", D(100), D(9))],
        )
        w.receive("r", 0, "origin", {"a": 10})
        w.register("m", 0, mission())
        w.reserve("reserve", 0, "m")
        with self.assertRaisesRegex(ValueError, "capacity"):
            w.start_loading("load", 0, "m", {"t": ("v", {"a": 10})})

    def test_refrigeration_compatibility_and_time(self):
        self.w.receive("r", 0, "origin", {"cold": 10, "warm": 10})
        self.w.register("m", 0, mission(item="cold"))
        self.w.reserve("reserve", 0, "m")
        self.rejected_unchanged(
            self.w.start_loading, "bad", 0, "m", {"t": ("v1", {"cold": 10})}
        )
        self.assertEqual(
            self.w.start_loading("load", 0, "m", {"t": ("cold-v", {"cold": 10})}),
            {"t": 900},
        )
        self.w.register("warm", 0, mission("warm-m", "warm"))
        self.w.reserve("warm-r", 0, "warm-m")
        self.rejected_unchanged(
            self.w.start_loading,
            "bad-warm",
            0,
            "warm-m",
            {"t2": ("cold-v", {"warm": 10})},
        )
        # A free refrigerated vehicle also rejects incompatible dry cargo.
        fresh = fixture()
        fresh.receive("r", 0, "origin", {"warm": 10})
        fresh.register("m", 0, mission(item="warm"))
        fresh.reserve("s", 0, "m")
        with self.assertRaisesRegex(ValueError, "incompatible"):
            fresh.start_loading("l", 0, "m", {"t": ("cold-v", {"warm": 10})})

    def test_load_timing_and_single_consumption(self):
        self.prepare()
        self.assertEqual(
            self.w.start_loading("l", 0, "m", {"t": ("v1", {"a": 10})}), {"t": 600}
        )
        self.rejected_unchanged(self.w.finish_loading, "early", 599, "t")
        manifest = self.w.finish_loading("done", 600, "t")
        self.assertEqual(sum(manifest.values()), 10)
        self.assertEqual(self.w.snapshot()["stock"]["origin"]["a"], 0)
        self.w.finish_loading("done", 600, "t")
        self.rejected_unchanged(self.w.finish_loading, "duplicate", 600, "t")
        self.assertEqual(sum(self.w.manifest("m").values()), 10)

    def test_total_duration_rounded_once(self):
        self.prepare(9, True)
        self.assertEqual(
            self.w.start_loading("l", 0, "m", {"t": ("v1", {"a": 9})}), {"t": 600}
        )

    def test_multi_vehicle_departure_gate_and_exclusivity(self):
        self.prepare()
        self.w.start_loading(
            "l", 0, "m", {"t1": ("v1", {"a": 4}), "t2": ("v2", {"a": 6})}
        )
        self.w.register("m2", 0, mission("other"))
        self.w.receive("more", 0, "origin", {"a": 10})
        self.w.reserve("reserve2", 0, "other")
        self.rejected_unchanged(
            self.w.start_loading, "busy", 0, "other", {"t3": ("v1", {"a": 10})}
        )
        self.w.finish_loading("f1", 600, "t1")
        self.rejected_unchanged(self.w.depart, "early", 600, "m")
        self.w.finish_loading("f2", 600, "t2")
        manifest = self.w.depart("go", 600, "m")
        self.assertEqual(sum(manifest.values()), 10)
        self.assertEqual(len(manifest), 2)
        self.assertEqual(len(self.w.snapshot()["busy"]), 2)

    def test_export_to_mission_outcome(self):
        self.prepare()
        self.w.start_loading("l", 0, "m", {"t": ("v1", {"a": 10})})
        self.w.finish_loading("f", 600, "t")
        manifest = self.w.depart("go", 600, "m")
        trip, batch, item = next(iter(manifest))
        delivery = Delivery("e", "run", "m", trip, batch, item, 5700, 5700, 9)
        result = self.w.evaluate("m", [delivery], 5700)
        self.assertEqual(result.delay_minutes, 35)
        self.assertEqual(result.onboard["a"], 1)
        self.assertFalse(result.logistics_complete)
        with self.assertRaises(ValueError):
            self.w.evaluate("m", [replace(delivery, occurred_s=599)], 5700)

    def test_integrated_demo_is_deterministic(self):
        from src.logistics.warehouse_demo import run_demo

        result = run_demo()
        self.assertEqual(result, run_demo())
        self.assertEqual(
            result["origin_stock_after_loading"], {"medium": 0, "large": 0}
        )
        self.assertEqual(result["outcomes"]["5700"]["delay_minutes"], 35)
        self.assertFalse(result["outcomes"]["5700"]["logistics_complete"])
        self.assertTrue(result["outcomes"]["6000"]["logistics_complete"])

    def test_late_plan_failure_rolls_back_every_vehicle(self):
        self.prepare()
        self.rejected_unchanged(
            self.w.start_loading,
            "bad",
            0,
            "m",
            {"first": ("v1", {"a": 5}), "second": ("remote-v", {"a": 5})},
        )
        self.w.start_loading("good", 0, "m", {"t": ("v1", {"a": 10})})
        self.assertEqual(len(self.w.snapshot()["busy"]), 1)

    def test_mixed_load_handling_duration(self):
        self.w = Warehouse(
            "run",
            [Item("a", D(10), D("0.04"), 60), Item("b", D(50), D("0.12"), 120)],
            [Store("origin", D(10), D(0)), Store("dest", D(10), D(0))],
            [Vehicle("v", "origin", D(1000), D(8))],
        )
        m = replace(
            mission(),
            lines=(MissionLine("a", 10, D("0.9")), MissionLine("b", 5, D("0.9"))),
        )
        self.w.receive("r", 0, "origin", {"a": 10, "b": 5})
        self.w.register("m", 0, m)
        self.w.reserve("s", 0, "m")
        self.assertEqual(
            self.w.start_loading("l", 0, "m", {"t": ("v", {"a": 10, "b": 5})}),
            {"t": 1500},
        )

    def test_snapshot_is_detached(self):
        self.prepare()
        snapshot = self.w.snapshot()
        snapshot["stock"]["origin"]["a"] = 1000
        snapshot["jobs"]["m"].reserved["a"] = 0
        self.assertEqual(self.w.available("origin", "a"), 0)

    def test_temporal_validation(self):
        self.w.receive("r", 1, "origin", {"a": 10})
        self.rejected_unchanged(self.w.receive, "past", 0, "origin", {"a": 1})
        self.rejected_unchanged(self.w.register, "late", 1, mission())
        self.rejected_unchanged(
            self.w.register,
            "foreign",
            1,
            replace(mission(), simulation_id="other", start_s=1),
        )

    def test_catalog_and_inputs(self):
        for q in [True, -1, 0, 1.2]:
            self.rejected_unchanged(self.w.receive, "bad", 0, "origin", {"a": q})
        for kwargs in [
            {"kg": D("NaN")},
            {"m3": D(0)},
            {"cold": 1},
            {"cold": True, "cold_compatible": False},
        ]:
            with self.assertRaises(ValueError):
                replace(Item("i", D(1), D(1), 30), **kwargs)
        self.rejected_unchanged(
            self.w.register,
            "dry",
            0,
            replace(mission(item="cold"), destination_id="dry"),
        )
        with self.assertRaises(ValueError):
            Warehouse("run", [Item("a", D(1), D(1), 30)] * 2, [], [])


if __name__ == "__main__":
    unittest.main()
