import unittest
from datetime import datetime, timezone
from decimal import Decimal as D

from src.logistics.calendars import Calendar
from src.logistics.core import Mission, MissionLine
from src.logistics.operations import DepotOperations
from src.logistics.roads import Network, Node, Road, NoRoute, reference_network
from src.logistics.transport import TransportWarehouse
from src.logistics.warehouse import Item, Store, Vehicle


def graph():
    return Network(
        [Node("a", 0, 0), Node("b", 1, 0), Node("c", 2, 0)],
        [Road("a", "b", 30), Road("b", "c", 30)],
        congestion_alpha=0,
    )


def fixture(network=None, positions=("a",), capacity=100, items=None):
    network = network or graph()
    return TransportWarehouse(
        "run",
        items or [Item("goods", D(1), D(1), 30)],
        [Store(n, D(1000), D(1000)) for n in network.nodes],
        [
            Vehicle(f"v{i }", p, D(capacity), D(capacity))
            for i, p in enumerate(positions)
        ],
        network=network,
        epoch=datetime(2026, 10, 5, tzinfo=timezone.utc),
        operations={n: DepotOperations(Calendar.daily(), 3) for n in network.nodes},
    )


def add(w, mid="m", origin="a", destination="c", q=10, start=0, urgent=False):
    w.receive("stock-" + mid, 0, origin, {"goods": q})
    m = Mission(
        "run",
        mid,
        origin,
        destination,
        start,
        3600 + start,
        (MissionLine("goods", q, D("0.9")),),
    )
    w.register("register-" + mid, 0, m, urgent)
    w.schedule("schedule-" + mid, 0, mid)


class NetworkTests(unittest.TestCase):
    def test_reference_reproducibility_and_alternatives(self):
        first, second = reference_network(17), reference_network(17)
        self.assertEqual(first.nodes, second.nodes)
        self.assertEqual(first.roads, second.roads)
        self.assertEqual(len(first.nodes), 25)
        self.assertEqual(len(first.roads), 40)
        self.assertNotEqual(first.nodes, reference_network(18).nodes)
        first.validate(alternatives=True)
        self.assertTrue(
            all(0 <= n.x_km <= 100 and 0 <= n.y_km <= 100 for n in first.nodes.values())
        )

    def test_shortest_time_not_distance(self):
        n = Network(
            [Node("a", 0, 0), Node("b", 1, 1), Node("c", 2, 0)],
            [Road("a", "c", 30), Road("a", "b", 70), Road("b", "c", 70)],
        )
        self.assertEqual(n.route("a", "c")[0], ("a", "b", "c"))
        n.set_condition("a", "b", closed=True)
        self.assertEqual(n.route("a", "c")[0], ("a", "c"))

    def test_crossing_geometry_is_not_connection(self):
        with self.assertRaises(ValueError):
            Network(
                [Node("a", 0, 0), Node("b", 2, 2), Node("c", 0, 2), Node("d", 2, 0)],
                [Road("a", "b", 30), Road("c", "d", 30)],
            )

    def test_conditions_and_congestion(self):
        n = Network([Node("a", 0, 0), Node("b", 1, 0)], [Road("a", "b", 30, 1)])
        self.assertEqual(n.seconds("a", "b"), 120)
        self.assertEqual(n.seconds("a", "b", {("a", "b"): 1}), 138)
        n.set_condition("a", "b", traffic=1.2, weather=1.1)
        self.assertEqual(n.seconds("a", "b"), 159)
        n.set_condition("a", "b", closed=True)
        with self.assertRaises(NoRoute):
            n.route("a", "b")

    def test_invalid_network(self):
        with self.assertRaises(ValueError):
            graph().validate(alternatives=True)
        with self.assertRaises(ValueError):
            Node("x", float("nan"), 0)
        with self.assertRaises(ValueError):
            Road("a", "b", 60)
        with self.assertRaises(ValueError):
            graph().set_condition("a", "b", traffic=-1)
        with self.assertRaises(ValueError):
            Network([Node("a", 0, 0), Node("a", 1, 1)], [])


class TransportTests(unittest.TestCase):
    def test_end_to_end_and_substep_arrivals(self):
        w = fixture()
        add(w)
        w.advance("complete", 1440)
        r = w.outcome("m", 1440)
        self.assertTrue(r.logistics_complete)
        self.assertEqual(r.quota_reached_s, 1440)  # 600 + 120 + 120 + 600
        self.assertEqual(w.snapshot()["stock"]["c"]["goods"], 10)
        self.assertEqual(w.snapshot()["positions"]["v0"], "c")
        self.assertFalse(w.snapshot()["busy"])

    def test_empty_repositioning_has_real_duration(self):
        w = fixture(positions=("c",))
        add(w, destination="b")
        w.advance("moving", 100)
        self.assertFalse(w.manifest("m"))
        self.assertIsNone(w.snapshot()["positions"]["v0"])
        w.advance("arrived-origin", 240)
        self.assertEqual(w.snapshot()["active"]["auto-1-0"]["start_s"], 240)
        w.advance("done", 1560)
        self.assertEqual(w.outcome("m", 1560).quota_reached_s, 1560)

    def test_nearest_available_vehicle(self):
        w = fixture(positions=("a", "c"))
        add(w)
        w.advance("allocate", 0)
        self.assertIn("v0", w.snapshot()["busy"])
        self.assertNotIn("v1", w.snapshot()["busy"])

    def test_multiple_vehicles_and_capacity(self):
        w = fixture(positions=("a", "a"), capacity=6)
        add(w)
        w.advance("done", 1500)
        self.assertEqual(len(w.manifest("m")), 2)
        self.assertEqual(sum(w.manifest("m").values()), 10)
        self.assertTrue(w.outcome("m", 1500).logistics_complete)
        self.assertFalse(w.snapshot()["busy"])

    def test_no_partial_fleet_claim_on_failed_plan(self):
        w = fixture(capacity=6)
        add(w)
        w.advance("wait", 1000)
        self.assertFalse(w.snapshot()["busy"])
        self.assertFalse(w.manifest("m"))
        self.assertEqual(
            w.snapshot()["allocation_wait"]["m"], "no_feasible_greedy_plan"
        )

    def test_urgent_assignment_first(self):
        w = fixture()
        add(w, "normal")
        add(w, "urgent", urgent=True)
        w.advance("allocate", 0)
        assignments = [
            e for e in w.snapshot()["transport_log"] if e["kind"] == "assignment"
        ]
        self.assertEqual([e["mission_id"] for e in assignments], ["urgent"])

    def test_future_start(self):
        w = fixture()
        add(w, start=1000)
        w.advance("before", 999)
        self.assertFalse(w.snapshot()["busy"])
        w.advance("start", 1000)
        self.assertTrue(w.snapshot()["busy"])

    def test_closed_route_waits_and_recovers(self):
        w = fixture()
        add(w)
        w.road_condition("close", 0, "a", "b", closed=True)
        w.advance("loaded", 600)
        self.assertEqual(w.snapshot()["allocation_wait"]["m"], "road_closed")
        self.assertFalse(w.snapshot()["road_movements"])
        w.road_condition("open", 700, "a", "b", closed=False)
        w.advance("done", 1540)
        self.assertEqual(w.outcome("m", 1540).quota_reached_s, 1540)

    def test_current_arc_finishes_before_closure_is_considered(self):
        w = fixture()
        add(w)
        w.advance("departed", 600)
        w.road_condition("close-next", 650, "b", "c", closed=True)
        w.advance("at-node", 720)
        movement = w.snapshot()["road_movements"]["v0"]
        self.assertEqual(movement["node"], "b")
        self.assertTrue(movement["blocked"])
        self.assertEqual(w.snapshot()["positions"]["v0"], "b")
        w.road_condition("open", 1000, "b", "c", closed=False)
        w.advance("done", 1720)
        self.assertTrue(w.outcome("m", 1720).logistics_complete)

    def test_mid_arc_traffic_does_not_teleport_vehicle(self):
        w = fixture()
        add(w)
        w.advance("departed", 600)
        w.road_condition("traffic", 650, "a", "b", traffic=10)
        w.advance("node", 720)
        exits = [e for e in w.snapshot()["transport_log"] if e["kind"] == "edge_exit"]
        self.assertEqual(exits[0]["at_s"], 720)
        self.assertEqual(exits[0]["node"], "b")

    def reroute_case(self, factor=None, closed=False, distance=10):
        n = Network(
            [
                Node("a", 0, 0),
                Node("b", 1, 0),
                Node("c", 1 + distance, 0),
                Node("d", 1 + distance / 2, 1),
            ],
            [
                Road("a", "b", 30),
                Road("b", "c", 30),
                Road("b", "d", 30),
                Road("d", "c", 30),
            ],
            congestion_alpha=0,
        )
        w = fixture(n)
        add(w)
        w.advance("depart", 600)
        w.road_condition("change", 650, "b", "c", traffic=factor or 1, closed=closed)
        w.advance("decision", 720)
        return [e for e in w.snapshot()["transport_log"] if e["kind"] == "reroute"]

    def test_reroute_requires_five_minutes(self):
        self.assertFalse(self.reroute_case(1.2))

    def test_reroute_requires_ten_percent(self):
        self.assertFalse(self.reroute_case(1.08, distance=40))

    def test_reroute_with_both_thresholds(self):
        changes = self.reroute_case(1.3)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["new_path"], ("b", "d", "c"))
        self.assertEqual(changes[0]["reason"], "time_saving")
        self.assertEqual(changes[0]["at_s"], 720)

    def test_closed_road_forces_even_slower_alternative(self):
        changes = self.reroute_case(closed=True)
        self.assertEqual(changes[0]["new_path"], ("b", "d", "c"))
        self.assertEqual(changes[0]["reason"], "road_closed")

    def test_cold_cargo_packed_before_flexible_cargo(self):
        w = TransportWarehouse(
            "run",
            [Item("cold", D(1), D(1), 30, True), Item("dry", D(1), D(1), 30)],
            [Store(n, D(100), D(100)) for n in ("a", "b", "c")],
            [
                Vehicle("cold-first", "a", D(10), D(10), True),
                Vehicle("dry-second", "a", D(10), D(10)),
            ],
            network=graph(),
            epoch=datetime(2026, 10, 5, tzinfo=timezone.utc),
            operations={
                n: DepotOperations(Calendar.daily(), 2) for n in ("a", "b", "c")
            },
        )
        w.receive("r", 0, "a", {"cold": 10, "dry": 10})
        m = Mission(
            "run",
            "mixed",
            "a",
            "c",
            0,
            3600,
            (MissionLine("cold", 10, D(1)), MissionLine("dry", 10, D(1))),
        )
        w.register("m", 0, m)
        w.schedule("s", 0, "mixed")
        w.advance("go", 0)
        loads = w.snapshot()["loads"]
        by_vehicle = {entry.vehicle_id: entry.quantities for entry in loads.values()}
        self.assertEqual(by_vehicle["cold-first"], {"cold": 10})
        self.assertEqual(by_vehicle["dry-second"], {"dry": 10})
        w.advance("done", 3000)
        self.assertTrue(w.outcome("mixed", 3000).logistics_complete)

    def test_retry_and_rejected_manual_arrival(self):
        w = fixture()
        add(w)
        w.advance("done", 1440)
        before = w.snapshot()
        w.advance("done", 1440)
        self.assertEqual(w.snapshot(), before)
        with self.assertRaises(ValueError):
            w.arrive("teleport", 1440, "auto-1-0")
        with self.assertRaises(ValueError):
            w.road_condition("invalid", 1500, "a", "b", traffic=-2)
        self.assertEqual(w.snapshot(), before)

    def test_cancellation_during_empty_travel(self):
        w = fixture(positions=("c",))
        add(w)
        w.advance("begin", 0)
        w.cancel("cancel", 60, "m")
        self.assertEqual(w.available("a", "goods"), 10)
        self.assertTrue(w.snapshot()["busy"])
        w.advance("arrive", 240)
        self.assertFalse(w.snapshot()["busy"])
        self.assertFalse(w.snapshot()["road_movements"])
        self.assertEqual(w.snapshot()["positions"]["v0"], "a")

    def test_reference_demo_repeats_with_real_empty_travel(self):
        from src.logistics.transport_demo import run_demo

        first = run_demo()
        self.assertEqual(first, run_demo())
        self.assertEqual((first["nodes"], first["roads"], first["fleet"]), (25, 40, 10))
        self.assertTrue(first["outcome"]["logistics_complete"])
        self.assertEqual(first["destination_stock"]["cold-small"], 10)
        self.assertTrue(first["empty_legs"])
        self.assertFalse(first["busy_vehicles"])

    def test_chunked_advance_same_as_single(self):
        a, b = fixture(), fixture()
        add(a)
        add(b)
        a.advance("all", 1440)
        for t in (100, 600, 650, 720, 800, 840, 1000, 1440):
            b.advance("step-" + str(t), t)
        self.assertEqual(a.outcome("m", 1440), b.outcome("m", 1440))
        self.assertEqual(a.snapshot()["transport_log"], b.snapshot()["transport_log"])


if __name__ == "__main__":
    unittest.main()
