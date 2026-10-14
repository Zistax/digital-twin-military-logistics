import unittest

from src.logistics.calendars import Calendar
from tests.test_supply import build, mission


class WaitDiagnosticTests(unittest.TestCase):
    def test_supplier_closed_depot_time_starts_at_actual_arrival(self):
        w = build(calendar=Calendar.daily(10 * 3600, 18 * 3600))
        w.order_supply("order", 0, "s", "origin", {"a": 10}, 100)
        w.advance("done", 7800)
        self.assertEqual(
            w.snapshot()["supply_wait_seconds"]["s"],
            {"opening": 7100, "berth": 0, "space": 0},
        )

    def test_supplier_full_warehouse_explains_wait(self):
        w = build(capacity=10)
        w.receive("stock", 0, "origin", {"a": 10})
        w.order_supply("order", 0, "s", "origin", {"a": 5}, 0)
        w.advance("blocked", 1000)
        self.assertEqual(w.snapshot()["supply_wait_seconds"]["s"]["space"], 1000)

    def test_shared_berth_wait_and_partition_invariance(self):
        def make():
            w = build()
            w.order_supply("one", 0, "s1", "origin", {"a": 10}, 0)
            w.order_supply("two", 0, "s2", "origin", {"a": 1}, 0)
            return w

        a, b = make(), make()
        a.advance("all", 900)
        for t in (100, 300, 600, 900):
            b.advance("part" + str(t), t)
        self.assertEqual(
            a.snapshot()["supply_wait_seconds"], b.snapshot()["supply_wait_seconds"]
        )
        self.assertEqual(a.snapshot()["supply_wait_seconds"]["s2"]["berth"], 600)

    def test_stock_wait_before_vehicle_assignment_is_measured(self):
        w = build()
        mission(w)
        w.advance("blocked", 1000)
        self.assertEqual(w.snapshot()["mission_wait_seconds"]["m"]["stock"], 1000)


if __name__ == "__main__":
    unittest.main()
