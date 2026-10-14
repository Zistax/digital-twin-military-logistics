import unittest
from datetime import datetime, timezone
from decimal import Decimal as D

from src.logistics.calendars import Calendar
from src.logistics.core import Mission, MissionLine
from src.logistics.operations import DepotOperations, OperationsWarehouse
from src.logistics.warehouse import Item, Store, Vehicle

EPOCH = datetime(2026, 10, 5, 6, tzinfo=timezone.utc)  # Monday 08:00 Rome


def build(calendar=None, berths=1, dest_capacity=10, quarantine=2):
    calendar = calendar or Calendar.daily()
    return OperationsWarehouse(
        "run",
        [Item("a", D(1), D(1), 30)],
        [Store("origin", D(100), D(0)), Store("dest", D(dest_capacity), D(0))],
        [
            Vehicle("v1", "origin", D(100), D(100)),
            Vehicle("v2", "origin", D(100), D(100)),
            Vehicle("v3", "origin", D(100), D(100)),
        ],
        epoch=EPOCH,
        operations={
            "origin": DepotOperations(calendar, berths, D(quarantine)),
            "dest": DepotOperations(calendar, berths, D(quarantine)),
        },
    )


def mission(mid="m", quantity=10, deadline=3600, start=0):
    return Mission(
        "run",
        mid,
        "origin",
        "dest",
        start,
        deadline,
        (MissionLine("a", quantity, D("0.9")),),
    )


def prepare(w, mid="m", q=10, vehicle="v1", urgent=False, at=0):
    w.receive(f"receipt-{mid}", at, "origin", {"a": q})
    w.register(f"register-{mid}", at, mission(mid, q, start=at), urgent)
    w.reserve(f"reserve-{mid}", at, mid)
    w.queue_loading(f"queue-{mid}", at, mid, {mid: (vehicle, {"a": q})})


def loaded(w):
    prepare(w)
    w.advance("load", 600)
    w.depart("go", 600, "m")


class OperationsTests(unittest.TestCase):
    def assert_rejected(self, w, fn, *args):
        before = w.snapshot()
        with self.assertRaises(ValueError):
            fn(*args)
        self.assertEqual(before, w.snapshot())

    def test_closed_arrival_and_overtime(self):
        cal = Calendar.daily(8 * 3600, 9 * 3600)
        w = build(cal)
        loaded(w)
        w.arrive("arrive", 3500, "m")
        w.advance("unload", 4100)
        self.assertTrue(w.outcome("m", 4100).logistics_complete)
        self.assertEqual(w.snapshot()["operations"][-1]["overtime_s"], 500)
        self.assertEqual(w.snapshot()["stock"]["dest"]["a"], 10)

    def test_exact_closing_waits_next_day(self):
        w = build(Calendar.daily(8 * 3600, 9 * 3600))
        loaded(w)
        w.arrive("arrive", 3600, "m")
        w.advance("wait", 86400)
        self.assertEqual(w.snapshot()["wait_seconds"]["m"]["opening"], 82800)
        self.assertEqual(w.snapshot()["active"]["m"]["start_s"], 86400)
        w.advance("finish", 87000)
        self.assertTrue(w.outcome("m", 87000).logistics_complete)

    def test_weekend_and_dst(self):
        cal = Calendar.daily(8 * 3600, 17 * 3600, range(5))
        friday = datetime(2026, 10, 23, 15, tzinfo=timezone.utc)  # Fri 17:00
        # DST ends Sunday: 63 local hours span 64 elapsed hours.
        self.assertFalse(cal.is_open(friday, 0))
        next_open = cal.next_change(friday, 0)
        self.assertEqual(next_open, 64 * 3600)
        self.assertTrue(cal.is_open(friday, next_open))

    def test_berth_serialization_and_priority(self):
        w = build()
        prepare(w, "normal", 10, "v1")
        prepare(w, "urgent", 10, "v2", True)
        w.advance("dispatch", 0)
        self.assertEqual(set(w.snapshot()["active"]), {"urgent"})
        w.advance("finish", 1200)
        self.assertEqual(w.snapshot()["wait_seconds"]["normal"]["berth"], 600)
        self.assertEqual(
            [op["trip_id"] for op in w.snapshot()["operations"]], ["urgent", "normal"]
        )

    def test_no_preemption_of_active_operation(self):
        w = build()
        prepare(w, "normal", 10, "v1")
        w.advance("begin", 0)
        prepare(w, "urgent", 10, "v2", True, at=100)
        w.advance("dispatch", 100)
        self.assertEqual(set(w.snapshot()["active"]), {"normal"})
        w.advance("finish", 1200)
        self.assertEqual(w.snapshot()["operations"][0]["trip_id"], "normal")

    def test_partial_unload_reserves_capacity_and_keeps_vehicle(self):
        w = build(dest_capacity=5)
        loaded(w)
        w.arrive("arrive", 601, "m")
        w.advance("partial", 1201)
        state = w.snapshot()
        self.assertEqual(state["stock"]["dest"]["a"], 5)
        self.assertEqual(w.outcome("m", 1201).onboard["a"], 5)
        self.assertIn("v1", state["busy"])
        self.assertFalse(state["active"])
        w.advance("wait", 1501)
        self.assertEqual(w.snapshot()["wait_seconds"]["m"]["space"], 300)

    def test_space_reserved_across_parallel_unloads(self):
        w = build(berths=2, dest_capacity=10)
        prepare(w, "one", 10, "v1")
        prepare(w, "two", 10, "v2")
        w.advance("load", 600)
        w.depart("go1", 600, "one")
        w.depart("go2", 600, "two")
        w.arrive("arr1", 601, "one")
        w.arrive("arr2", 601, "two")
        w.advance("dispatch", 601)
        self.assertEqual(len(w.snapshot()["active"]), 1)
        self.assert_rejected(w, w.receive, "overbook", 601, "dest", {"a": 1})
        w.advance("done", 1201)
        self.assertEqual(w.snapshot()["stock"]["dest"]["a"], 10)
        self.assertEqual(w.outcome("two", 1201).onboard["a"], 10)

    def test_quarantine_and_removal_unblock_cargo(self):
        w = build(quarantine=1)
        loaded(w)
        w.arrive("arrive", 601, "m", {"a": 2})
        w.advance("first", 1201)
        self.assertEqual(w.snapshot()["stock"]["dest"]["a"], 8)
        self.assertEqual(w.snapshot()["quarantine"]["dest"]["a"], 1)
        self.assertEqual(w.outcome("m", 1201).onboard["a"], 1)
        w.advance("remove-and-unload", 88201)
        state = w.snapshot()
        self.assertFalse(state["busy"])
        self.assertEqual(w.outcome("m", 88201).unusable["a"], 2)
        self.assertIsNone(w.outcome("m", 88201).delay_minutes)
        self.assertTrue(
            any(op["kind"] == "quarantine_removal" for op in state["operations"])
        )

    def test_release_at_destination_and_reuse_shared_berth(self):
        w = build(dest_capacity=10)
        loaded(w)
        w.arrive("arrive", 601, "m")
        w.advance("finish", 1201)
        self.assertFalse(w.snapshot()["busy"])
        self.assertEqual(w.snapshot()["positions"]["v1"], "dest")
        out = Mission(
            "run", "out", "dest", "origin", 1201, 6000, (MissionLine("a", 10, D(1)),)
        )
        w.register("out", 1201, out)
        w.reserve("out-reserve", 1201, "out")
        w.queue_loading("out-queue", 1201, "out", {"out": ("v1", {"a": 10})})
        w.advance("out-load", 1801)
        self.assertEqual(w.snapshot()["stock"]["dest"]["a"], 0)
        w.depart("out-go", 1801, "out")
        w.arrive("out-arrive", 2000, "out")
        w.advance("out-finish", 2600)
        self.assertTrue(w.outcome("out", 2600).logistics_complete)
        self.assertEqual(w.snapshot()["stock"]["origin"]["a"], 10)

    def test_retry_rollback_and_bypass_prevention(self):
        w = build()
        loaded(w)
        self.assert_rejected(w, w.arrive, "bad", 700, "m", {"a": 11})
        w.arrive("arrive", 700, "m")
        before = w.snapshot()
        w.arrive("arrive", 700, "m")
        self.assertEqual(before, w.snapshot())
        self.assert_rejected(w, w.arrive, "twice", 700, "m")
        with self.assertRaises(ValueError):
            w.finish_loading("manual", 700, "m")
        with self.assertRaises(ValueError):
            w.start_loading("manual", 700, "m", {})

    def test_past_outcome_does_not_include_future_loads(self):
        w = build()
        loaded(w)
        result = w.outcome("m", 0)
        self.assertEqual(result.onboard["a"], 0)
        self.assertFalse(result.logistics_complete)
        with self.assertRaises(ValueError):
            w.outcome("m", 1000)

    def test_waiting_reserves_can_be_preempted_but_active_cannot(self):
        w = build()
        w.receive("stock", 0, "origin", {"a": 10})
        w.register("normal", 0, mission())
        w.reserve("reserve", 0, "m")
        w.queue_loading(
            "queue", 0, "m", {"t1": ("v1", {"a": 5}), "t2": ("v2", {"a": 5})}
        )
        w.advance("start", 0)
        w.register("urgent", 1, mission("u", 5, start=1), True)
        transfers = w.reserve("steal", 1, "u")["transfers"]
        self.assertEqual(transfers, [("m", "a", 5)])
        w.advance("finish-active", 600)
        self.assertEqual(w.snapshot()["loads"]["t1"].status, "loaded")
        self.assertEqual(w.snapshot()["loads"]["t2"].status, "queued")
        w.receive("restore", 600, "origin", {"a": 5})
        w.reserve("rereserve", 600, "m")
        w.advance("finish-second", 1200)
        w.depart("go", 1200, "m")
        self.assertEqual(sum(w.manifest("m").values()), 10)

    def test_partial_unload_resumes_and_demo_is_repeatable(self):
        from src.logistics.operations_demo import run_demo

        result = run_demo()
        self.assertEqual(result, run_demo())
        self.assertEqual(result["partial_at_10_10"]["onboard"]["a"], 5)
        self.assertEqual(result["final_at_10_30"]["delay_minutes"], 10)
        self.assertTrue(result["delivery_vehicle_free"])
        self.assertEqual(result["waiting_seconds"]["opening"], 3600)
        self.assertEqual(result["waiting_seconds"]["space"], 600)
        # Two actual unload visits each incur their own preparation time.
        unloads = [op for op in result["operations"] if op["kind"] == "unload"]
        self.assertEqual(len(unloads), 2)
        self.assertTrue(all(op["end_s"] - op["start_s"] == 600 for op in unloads))

    def test_queued_cancellation_frees_vehicle_and_stock(self):
        w = build()
        prepare(w)
        w.cancel("cancel", 0, "m")
        self.assertFalse(w.snapshot()["busy"])
        self.assertFalse(w.snapshot()["queue"])
        self.assertEqual(w.available("origin", "a"), 10)
        w.advance("later", 1200)
        self.assertFalse(w.snapshot()["operations"])

    def test_urgent_plan_does_not_strand_new_reservations(self):
        w = build()
        w.receive("r", 0, "origin", {"a": 9})
        w.register("m", 0, mission(), True)
        w.reserve("s", 0, "m")
        w.queue_loading("q", 0, "m", {"t": ("v1", {"a": 9})})
        w.receive("extra", 0, "origin", {"a": 1})
        w.reserve("s2", 0, "m")
        w.advance("load", 600)
        w.depart("go", 600, "m")
        self.assertEqual(w.available("origin", "a"), 1)
        self.assertEqual(w.snapshot()["jobs"]["m"].reserved["a"], 0)

    def test_quarantine_removal_waits_for_opening(self):
        w = build(Calendar.daily(8 * 3600, 9 * 3600))
        loaded(w)
        w.arrive("arrive", 3500, "m", {"a": 1})
        w.advance("finish", 4100)
        # Unload ended after closure. Its 24h expiry is also outside opening.
        w.advance("expiry", 90500)
        self.assertEqual(w.snapshot()["quarantine"]["dest"]["a"], 1)
        w.advance("next-opening", 172800)
        self.assertEqual(w.snapshot()["quarantine"]["dest"]["a"], 0)

    def test_cold_space_not_substituted_with_ordinary(self):
        w = OperationsWarehouse(
            "run",
            [Item("a", D(1), D(1), 30, True)],
            [Store("origin", D(100), D(10)), Store("dest", D(100), D(5))],
            [Vehicle("v1", "origin", D(100), D(100), True)],
            epoch=EPOCH,
            operations={
                d: DepotOperations(Calendar.daily()) for d in ("origin", "dest")
            },
        )
        prepare(w)
        w.advance("load", 900)
        w.depart("go", 900, "m")
        w.arrive("arrive", 1000, "m")
        w.advance("partial", 1900)
        self.assertEqual(w.snapshot()["stock"]["dest"]["a"], 5)
        self.assertEqual(w.outcome("m", 1900).onboard["a"], 5)
        self.assertEqual(w.snapshot()["operations"][-1]["end_s"], 1900)

    def test_deadline_at_unload_completion_is_on_time(self):
        w = build()
        loaded(w)
        w.arrive("arrive", 3000, "m")
        w.advance("finish", 3600)
        self.assertFalse(w.outcome("m", 3600).late)
        self.assertEqual(w.outcome("m", 3600).delay_minutes, 0)
        # Once recorded, future queries cannot retroactively change the deadline.
        self.assertIsNone(w.outcome("m", 3599).late)

    def test_configuration_rejected(self):
        for windows in [(), ((0, 10, 10),), ((7, 0, 1),), ((0, 0, 10), (0, 5, 20))]:
            with self.assertRaises(ValueError):
                Calendar(windows)
        with self.assertRaises(ValueError):
            DepotOperations(Calendar.daily(), 0)


if __name__ == "__main__":
    unittest.main()
