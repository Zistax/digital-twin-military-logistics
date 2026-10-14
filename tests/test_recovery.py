import unittest
from dataclasses import replace
from unittest.mock import patch
from datetime import datetime, timezone
from decimal import Decimal as D

from src.logistics.calendars import Calendar
from src.logistics.core import Mission, MissionLine
from src.logistics.incidents import IncidentPolicy, hourly_probability
from src.logistics.operations import DepotOperations
from src.logistics.recovery import RecoveryWarehouse
from src.logistics.roads import Network, Node, Road
from src.logistics.warehouse import Item, Store, Vehicle


def fixture(cold=False, distance=10, quarantine=100, policy=None, items=None):
    items = items or [Item("a", D(1), D(1), 30, cold)]
    return RecoveryWarehouse(
        "run",
        items,
        [Store("origin", D(100), D(100)), Store("dest", D(100), D(100))],
        [
            Vehicle("v0", "origin", D(100), D(100), cold),
            Vehicle("v1", "origin", D(100), D(100), cold),
        ],
        network=Network(
            [Node("origin", 0, 0), Node("dest", distance, 0)],
            [Road("origin", "dest", 30)],
            congestion_alpha=0,
        ),
        epoch=datetime(2026, 10, 5, tzinfo=timezone.utc),
        operations={
            d: DepotOperations(Calendar.daily(), 1, D(quarantine), D(quarantine))
            for d in ("origin", "dest")
        },
        incident_policy=policy,
        categories={item.item_id: "cold" if item.cold else "spares" for item in items},
    )


def prepare(w):
    w.receive("stock", 0, "origin", {"a": 20})
    w.register(
        "m",
        0,
        Mission(
            "run", "m", "origin", "dest", 0, 2500, (MissionLine("a", 10, D("0.9")),)
        ),
    )
    w.schedule("s", 0, "m")
    w.advance("travel", 1000)


class RecoveryTests(unittest.TestCase):
    def test_multi_item_split_and_partition_invariance(self):
        def make():
            w = fixture(items=[Item("a", D(1), D(1), 30), Item("b", D(1), D(1), 30)])
            w._vehicles["v1"] = replace(w._vehicles["v1"], max_kg=D(6), max_m3=D(6))
            w.receive("stock", 0, "origin", {"a": 5, "b": 5})
            w.register(
                "mission",
                0,
                Mission(
                    "run",
                    "m",
                    "origin",
                    "dest",
                    0,
                    20000,
                    (MissionLine("a", 5, D(1)), MissionLine("b", 5, D(1))),
                ),
            )
            w.schedule("schedule", 0, "m")
            w.breakdown("failure", 1000, "v0", False, 86400)
            w.decide("yes", 1100, "request-1", "approve")
            return w

        a, b = make(), make()
        a.advance("all", 20000)
        for t in (2000, 3000, 4000, 6000, 10000, 20000):
            b.advance("part" + str(t), t)
        self.assertEqual(a.outcome("m", 20000).accepted, {"a": 5, "b": 5})
        self.assertEqual(a.outcome("m", 20000), b.outcome("m", 20000))
        self.assertEqual(a.snapshot()["batch_splits"], b.snapshot()["batch_splits"])
        self.assertEqual(a.observed_incidents(), b.observed_incidents())
        self.assertEqual(a.outcome("m", 1000).onboard, {"a": 5, "b": 5})

    def test_split_child_failure_and_second_split_preserve_past_outcome(self):
        w = fixture()
        for v, capacity in (("v1", 6), ("v2", 4), ("v3", 2)):
            w._vehicles[v] = Vehicle(v, "origin", D(capacity), D(capacity))
            w._positions[v] = "origin"
        prepare(w)
        w.breakdown("original", 1000, "v0", False, 86400)
        w.decide("yes", 1100, "request-1", "approve")
        w.advance("first-split", 2750)
        past = w.outcome("m", 2750)
        w.breakdown("child", 2800, "v1", False, 86400)
        w.decide("yes-child", 2800, "request-2", "approve")
        w.advance("done", 30000)
        self.assertEqual(w.outcome("m", 30000).accepted["a"], 10)
        self.assertEqual(w.outcome("m", 2750), past)
        self.assertGreaterEqual(len(w.snapshot()["batch_splits"]), 2)
        self.assertEqual(sum(w.manifest("m").values()), 10)

    def test_cancel_during_split_recovery_does_not_abandon_residue(self):
        w = fixture()
        w._vehicles["v1"] = replace(w._vehicles["v1"], max_kg=D(4), max_m3=D(4))
        prepare(w)
        w.breakdown("original", 1000, "v0", False, 86400)
        w.decide("yes", 1100, "request-1", "approve")
        w.cancel("cancel", 3000, "m")
        w.advance("done", 20000)
        result = w.outcome("m", 20000)
        self.assertEqual(result.status, "cancelled")
        self.assertEqual(result.accepted["a"], 10)
        self.assertEqual(result.onboard["a"], 0)

    def test_split_recovery_preserves_history_damage_and_total(self):
        w = fixture()
        w._vehicles["v1"] = replace(w._vehicles["v1"], max_kg=D(6), max_m3=D(6))
        w._vehicles["v2"] = Vehicle("v2", "origin", D(6), D(6))
        w._positions["v2"] = "origin"
        prepare(w)
        w.damage_cargo("damage", 1000, "auto-1-0", "a", 2)
        before = w.outcome("m", 1000)
        w.breakdown("failure", 1000, "v0", False, 86400)
        w.decide("yes", 1100, "request-1", "approve")
        w.advance("done", 10000)
        result = w.outcome("m", 10000)
        self.assertEqual(result.accepted["a"], 8)
        self.assertEqual(result.unusable["a"], 2)
        self.assertEqual(result.onboard["a"], 0)
        self.assertEqual(sum(w.manifest("m").values()), 10)
        self.assertEqual(w.outcome("m", 1000), before)
        state = w.snapshot()
        self.assertEqual(len(state["batch_splits"]), 1)
        self.assertEqual(
            {t["vehicle_id"] for t in state["requests"]["request-1"]["transfers"]},
            {"v1", "v2"},
        )
        self.assertEqual(state["requests"]["request-2"]["quantities"], {"a": 1})

    def test_split_recovery_can_reuse_one_small_vehicle(self):
        w = fixture()
        w._vehicles["v1"] = replace(w._vehicles["v1"], max_kg=D(4), max_m3=D(4))
        prepare(w)
        w.breakdown("failure", 1000, "v0", False, 100)
        w.decide("yes", 1100, "request-1", "approve")
        w.advance("done", 20000)
        self.assertEqual(w.outcome("m", 20000).accepted["a"], 10)
        self.assertTrue(w.outcome("m", 20000).logistics_complete)
        self.assertEqual(len(w.snapshot()["batch_splits"]), 2)
        self.assertNotIn("v0", w.snapshot()["busy"])

    def test_split_cold_exposure_is_inherited(self):
        w = fixture(cold=True, distance=100)
        w._vehicles["v1"] = replace(w._vehicles["v1"], max_kg=D(6), max_m3=D(6))
        prepare(w)
        w.cold_outage("cold", 1000, "v0", 1000)
        w.breakdown("failure", 1000, "v0", False, 86400)
        w.decide("yes", 1100, "request-1", "approve")
        w.advance("split", 3000)
        split = w.snapshot()["batch_splits"][0]
        self.assertEqual(w.snapshot()["cold_exposure"][split["child"]], 1000)
        self.assertEqual(w.snapshot()["cold_exposure"][split["parent"]], 1000)

    def test_rescuer_failure_during_travel_to_endpoint(self):
        for repairable in (True, False):
            with self.subTest(repairable=repairable):
                w = fixture()
                w._network = Network(
                    [Node("origin", 10, 0), Node("dest", 20, 0), Node("hub", 0, 0)],
                    [Road("origin", "dest", 30), Road("hub", "origin", 30)],
                    congestion_alpha=0,
                )
                w._positions["v1"] = "hub"
                prepare(w)
                w.breakdown("original", 1000, "v0", False, 86400)
                w.decide("yes", 1100, "request-1", "approve")
                w.breakdown("rescuer", 1200, "v1", repairable, 500)
                w.advance("done", 10000)
                self.assertEqual(w.outcome("m", 10000).accepted["a"], 10)
                self.assertEqual(len(w.snapshot()["requests"]), 1)

    def test_cancel_during_interrupted_rescue_still_unloads_cargo(self):
        w = fixture()
        prepare(w)
        w.breakdown("original", 1000, "v0", False, 86400)
        w.decide("yes", 1100, "request-1", "approve")
        w.breakdown("rescuer", 1200, "v1", True, 500)
        w.cancel("cancel", 1300, "m")
        w.advance("done", 4600)
        self.assertEqual(w.outcome("m", 4600).status, "cancelled")
        self.assertEqual(w.outcome("m", 4600).accepted["a"], 10)
        self.assertEqual(w.snapshot()["requests"]["request-1"]["status"], "completed")

    def test_second_loaded_failure_preserves_manifest(self):
        w = fixture()
        prepare(w)
        manifest = w.manifest("m")
        w.breakdown("original", 1000, "v0", False, 100)
        w.decide("yes", 1100, "request-1", "approve")
        w.breakdown("second", 2800, "v1", False, 86400)
        w.decide("yes-again", 2800, "request-2", "approve")
        w.advance("done", 10000)
        self.assertEqual(w.outcome("m", 10000).accepted["a"], 10)
        self.assertEqual(w.manifest("m"), manifest)
        self.assertEqual(w.snapshot()["loads"]["auto-1-0"].vehicle_id, "v0")

    def test_rescuer_repairable_failure_on_final_approach(self):
        w = fixture()
        prepare(w)
        original = w.manifest("m")
        w.breakdown("original", 1000, "v0", False, 86400)
        w.decide("yes", 1100, "request-1", "approve")
        w.breakdown("rescuer", 1200, "v1", True, 500)
        w.advance("done", 4600)
        self.assertEqual(w.outcome("m", 4600).quota_reached_s, 4600)
        self.assertEqual(w.manifest("m"), original)

    def test_rescuer_repairable_failure_during_transfer(self):
        w = fixture()
        prepare(w)
        w.breakdown("original", 1000, "v0", False, 86400)
        w.decide("yes", 1100, "request-1", "approve")
        w.breakdown("rescuer", 1600, "v1", True, 500)
        self.assertEqual(w.snapshot()["loads"]["auto-1-0"].vehicle_id, "v0")
        w.advance("done", 4600)
        self.assertEqual(w.outcome("m", 4600).quota_reached_s, 4600)

    def test_nonrepairable_rescuer_restarts_approved_recovery(self):
        for failed_s in (1200, 1600):
            with self.subTest(failed_s=failed_s):
                w = fixture()
                prepare(w)
                original = w.manifest("m")
                w.breakdown("original", 1000, "v0", False, 86400)
                w.decide("yes", 1100, "request-1", "approve")
                w.breakdown("rescuer", failed_s, "v1", False, 500)
                w.advance("wait", failed_s + 100)
                self.assertEqual(w.snapshot()["loads"]["auto-1-0"].vehicle_id, "v0")
                w.advance("done", 6000)
                self.assertEqual(w.outcome("m", 6000).accepted["a"], 10)
                self.assertEqual(w.manifest("m"), original)
                self.assertEqual(len(w.snapshot()["requests"]), 1)

    def test_automatic_rescuer_approach_clock_is_partition_invariant(self):
        def make():
            w = fixture(policy=IncidentPolicy(seed=5, automatic=True))
            w._drive_left = {"v0": 100000, "v1": 100}
            prepare(w)
            w.breakdown("original", 1000, "v0", False, 86400)
            w.decide("yes", 1100, "request-1", "approve")
            return w

        a, b = make(), make()
        a.advance("all", 12000)
        for t in (1150, 1200, 1500, 2000, 5000, 12000):
            b.advance("part" + str(t), t)
        self.assertEqual(a.observed_incidents(), b.observed_incidents())
        self.assertEqual(a.outcome("m", 12000), b.outcome("m", 12000))
        self.assertTrue(
            any(
                e.get("rescue_stage") == "approach"
                for e in a.observed_incidents()["alerts"]
            )
        )

    def test_two_articles_same_outage_different_tolerances(self):
        w = fixture(
            cold=True,
            distance=100,
            items=[
                Item("a", D(1), D(1), 30, True, cold_tolerance_s=100),
                Item("b", D(1), D(1), 30, True, cold_tolerance_s=200),
            ],
        )
        w.receive("stock", 0, "origin", {"a": 1, "b": 1})
        w.register(
            "mission",
            0,
            Mission(
                "run",
                "m",
                "origin",
                "dest",
                0,
                20000,
                (MissionLine("a", 1, D(1)), MissionLine("b", 1, D(1))),
            ),
        )
        w.schedule("schedule", 0, "m")
        w.advance("travel", 1000)
        w.cold_outage("outage", 1000, "v0", 201)
        w.advance("first", 1101)
        self.assertEqual(
            {k[2]: q for k, q in w.snapshot()["hidden_bad"].items()}, {"a": 1, "b": 0}
        )
        w.advance("second", 1201)
        self.assertEqual(
            {k[2]: q for k, q in w.snapshot()["hidden_bad"].items()}, {"a": 1, "b": 1}
        )

    def test_supply_shortfall_and_damage_remain_distinct(self):
        w = fixture()
        w.order_supply(
            "order", 0, "s", "origin", {"a": 10}, 0, actual_quantities={"a": 7}
        )
        with patch.object(w, "_supply_damage", return_value=2):
            w.advance("unloaded", 600)
        supply = w.snapshot()["supplies"]["s"]
        self.assertEqual(supply["not_delivered"]["a"], 3)
        self.assertEqual(supply["unusable"]["a"], 2)
        self.assertEqual(supply["received"]["a"], 7)
        self.assertEqual(w.inventory_position("origin", "a"), 5)

    def test_item_tolerance_overrides_policy_at_exact_boundary(self):
        w = fixture(cold=True, distance=100)
        w._items["a"] = replace(w._items["a"], cold_tolerance_s=100)
        prepare(w)
        w.cold_outage("outage", 1000, "v0", 200)
        w.advance("boundary", 1100)
        key = next(iter(w.manifest("m")))
        self.assertEqual(w.snapshot()["hidden_bad"][key], 0)
        w.advance("exceeded", 1101)
        self.assertEqual(w.snapshot()["hidden_bad"][key], 10)

    def test_item_tolerance_validation(self):
        for tolerance in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                Item("a", D(1), D(1), 30, True, cold_tolerance_s=tolerance)
        with self.assertRaises(ValueError):
            Item("a", D(1), D(1), 30, cold_tolerance_s=100)
        self.assertEqual(
            Item("a", D(1), D(1), 30, True, cold_tolerance_s=0).cold_tolerance_s, 0
        )

    def test_supplier_damage_is_quarantined_and_removed_after_24h(self):
        w = fixture()
        w.order_supply("order", 0, "s", "origin", {"a": 10}, 0)
        with patch.object(w, "_supply_damage", return_value=2) as damage:
            w.advance("unloaded", 600)
            damage.assert_called_once_with("s", "a", 10)
        state = w.snapshot()
        self.assertEqual(state["stock"]["origin"]["a"], 8)
        self.assertEqual(state["quarantine"]["origin"]["a"], 2)
        self.assertEqual(state["supplies"]["s"]["received"]["a"], 10)
        self.assertEqual(state["supplies"]["s"]["unusable"]["a"], 2)
        self.assertEqual(w.inventory_position("origin", "a"), 8)
        w.advance("before", 86999)
        self.assertEqual(w.snapshot()["quarantine"]["origin"]["a"], 2)
        w.advance("removed", 87000)
        self.assertEqual(w.snapshot()["quarantine"]["origin"]["a"], 0)
        w._check()

    def test_supplier_bad_residue_waits_without_redamage(self):
        w = fixture(quarantine=1)
        w.order_supply("order", 0, "s", "origin", {"a": 10}, 0)
        with patch.object(w, "_supply_damage", return_value=2) as damage:
            w.advance("unloaded", 600)
            s = w.snapshot()["supplies"]["s"]
            self.assertEqual(s["remaining"], {"a": 1})
            self.assertEqual(s["bad_remaining"], {"a": 1})
            self.assertFalse(w.snapshot()["active"])
            self.assertEqual(w.inventory_position("origin", "a"), 8)
            w.advance("second-unload", 87600)
            damage.assert_called_once_with("s", "a", 10)
        self.assertEqual(w.snapshot()["supplies"]["s"]["status"], "closed")
        self.assertEqual(w.snapshot()["supplies"]["s"]["unusable"]["a"], 2)
        w._check()

    def test_supplier_damage_without_quarantine_releases_berth(self):
        w = fixture(quarantine=0)
        w.order_supply("order", 0, "s", "origin", {"a": 10}, 0)
        with patch.object(w, "_supply_damage", return_value=2):
            w.advance("unloaded", 600)
        w.order_supply("next-order", 600, "s2", "origin", {"a": 1}, 600)
        w.advance("next-unloaded", 1200)
        self.assertEqual(w.snapshot()["stock"]["origin"]["a"], 9)
        self.assertEqual(w.snapshot()["supplies"]["s"]["bad_remaining"]["a"], 2)
        self.assertEqual(w.snapshot()["supplies"]["s2"]["status"], "closed")

    def test_supplier_damage_seeded_and_independent_of_time_partition(self):
        def make():
            w = fixture(policy=IncidentPolicy(seed=5, automatic=True))
            w._categories["a"] = "electronics"
            w.order_supply("order", 0, "s", "origin", {"a": 100}, 0)
            return w

        a, b = make(), make()
        a.advance("all", 3600)
        for t in (100, 1000, 3000, 3600):
            b.advance("part" + str(t), t)
        self.assertEqual(a.snapshot()["supplies"], b.snapshot()["supplies"])
        self.assertEqual(a.snapshot()["supply_log"], b.snapshot()["supply_log"])
        self.assertGreater(a.snapshot()["supplies"]["s"]["unusable"]["a"], 0)

    def test_repairable_breakdown_delays_without_losing_cargo(self):
        w = fixture()
        prepare(w)
        w.breakdown("failure", 1000, "v0", duration_s=900)
        w.advance("done", 3300)
        self.assertEqual(w.outcome("m", 3300).quota_reached_s, 3300)
        self.assertEqual(w.outcome("m", 3300).accepted["a"], 10)
        self.assertFalse(w.snapshot()["requests"])

    def test_no_replacement_without_approval(self):
        w = fixture()
        prepare(w)
        w.breakdown("failure", 1000, "v0", False, 86400)
        w.advance("wait", 10000)
        self.assertNotIn("v1", w.snapshot()["busy"])
        self.assertEqual(w.outcome("m", 10000).onboard["a"], 10)
        self.assertEqual(w.snapshot()["requests"]["request-1"]["status"], "pending")

    def test_substitute_reaches_site_and_keeps_same_batch(self):
        w = fixture()
        prepare(w)
        original = w.manifest("m")
        w.breakdown("failure", 1000, "v0", False, 86400)
        w.decide("approve", 1100, "request-1", "approve")
        w.advance("done", 4100)
        self.assertEqual(w.manifest("m"), original)
        self.assertEqual(w.outcome("m", 4100).accepted["a"], 10)
        self.assertEqual(w.snapshot()["loads"]["auto-1-0"].vehicle_id, "v1")
        self.assertIn("v0", w.snapshot()["busy"])
        w.advance("repair", 87400)
        self.assertNotIn("v0", w.snapshot()["busy"])
        self.assertEqual(w.snapshot()["positions"]["v0"], "origin")

    def test_restore_waits_until_cargo_managed(self):
        w = fixture()
        prepare(w)
        w.breakdown("failure", 1000, "v0", False, 100)
        w.advance("past-repair", 2000)
        self.assertIn("v0", w.snapshot()["broken_vehicles"])
        w.decide("approve", 2000, "request-1", "approve")
        w.advance("transfer", 3600)
        self.assertNotIn("v0", w.snapshot()["broken_vehicles"])

    def test_hidden_damage_and_supplement_only_to_minimum(self):
        w = fixture()
        prepare(w)
        w.damage_cargo("damage", 1000, "auto-1-0", "a", 2)
        self.assertFalse(
            any(a["kind"] == "inspection" for a in w.observed_incidents()["alerts"])
        )
        w.advance("inspect", 2400)
        self.assertEqual(w.outcome("m", 2400).accepted["a"], 8)
        request = w.snapshot()["requests"]["request-1"]
        self.assertEqual(request["quantities"], {"a": 1})
        w.decide("approve", 2400, "request-1", "approve")
        w.advance("finish", 4800)
        self.assertEqual(w.outcome("m", 4800).accepted["a"], 9)
        self.assertEqual(w.snapshot()["jobs"]["m"].mission.deadline_s, 2500)
        self.assertTrue(w.outcome("m", 4800).logistics_complete)
        self.assertEqual(len(w.manifest("m")), 2)

    def test_defer_and_reject_do_not_cancel_mission(self):
        w = fixture()
        prepare(w)
        w.damage_cargo("damage", 1000, "auto-1-0", "a", 2)
        w.advance("inspect", 2400)
        w.decide("defer", 2400, "request-1", "defer")
        w.decide("reject", 2500, "request-1", "reject")
        w.advance("wait", 6000)
        self.assertEqual(w.snapshot()["jobs"]["m"].status, "recovery_wait")
        self.assertEqual(w.outcome("m", 6000).accepted["a"], 8)

    def test_cold_exposure_accumulates_without_reset(self):
        w = fixture(cold=True, distance=100)
        prepare(w)
        w.cold_outage("first", 1000, "v0", 2000)
        w.advance("restored", 3000)
        w.cold_outage("second", 3500, "v0", 1601)
        w.advance("limit", 5100)
        key = next(iter(w.manifest("m")))
        self.assertEqual(w.snapshot()["cold_exposure"][key], 3600)
        self.assertEqual(w.snapshot()["hidden_bad"][key], 0)
        w.advance("over", 5101)
        self.assertEqual(w.snapshot()["hidden_bad"][key], 10)
        self.assertFalse(
            any(a["kind"] == "inspection" for a in w.observed_incidents()["alerts"])
        )

    def test_no_double_damage_and_quarantine_overflow(self):
        w = fixture(quarantine=0)
        prepare(w)
        w.damage_cargo("damage", 1000, "auto-1-0", "a", 2)
        with self.assertRaises(ValueError):
            w.damage_cargo("too-many", 1000, "auto-1-0", "a", 9)
        w.advance("inspect", 2400)
        self.assertEqual(w.outcome("m", 2400).accepted["a"], 8)
        self.assertEqual(w.outcome("m", 2400).onboard["a"], 2)
        self.assertFalse(w.snapshot()["active"])
        self.assertIn("v0", w.snapshot()["busy"])

    def test_demo_is_reproducible(self):
        from src.logistics.recovery_demo import run_demo

        result = run_demo()
        self.assertEqual(result, run_demo())
        self.assertEqual(result["first_delivery"]["accepted"]["spares"], 8)
        self.assertEqual(result["final_delivery"]["accepted"]["spares"], 9)
        self.assertFalse(result["busy"])
        self.assertEqual(result["original_vehicle_position"], "origin")

    def test_probability_composes_across_steps(self):
        p = hourly_probability(0.02, 300)
        self.assertAlmostEqual(1 - (1 - p) ** 12, 0.02)
        for value in (-1, 2, float("nan")):
            with self.assertRaises(ValueError):
                hourly_probability(value, 300)

    def test_batch_approval_is_hidden_and_reproducible(self):
        def run():
            w = fixture(policy=IncidentPolicy(seed=42, auto_approve=True))
            prepare(w)
            w.damage_cargo("d", 1000, "auto-1-0", "a", 2)
            w.advance("inspect", 2400)
            observed = w.observed_incidents()
            self.assertNotIn("due_s", observed["requests"]["request-1"])
            w.advance("finish", 12000)
            self.assertTrue(w.outcome("m", 12000).late)
            return w.snapshot()["requests"]

        self.assertEqual(run(), run())

    def test_damage_retry_idempotent(self):
        w = fixture()
        prepare(w)
        w.damage_cargo("damage", 1000, "auto-1-0", "a", 2)
        before = w.snapshot()
        w.damage_cargo("damage", 1000, "auto-1-0", "a", 2)
        self.assertEqual(before, w.snapshot())

    def test_cancel_in_transit_preserves_cargo_and_suppresses_recovery(self):
        w = fixture()
        prepare(w)
        w.damage_cargo("damage", 1000, "auto-1-0", "a", 2)
        w.cancel("cancel", 1000, "m", "scenario cancelled")
        self.assertEqual(w.outcome("m", 1000).onboard["a"], 10)
        w.advance("unload", 2400)
        result = w.outcome("m", 2400)
        self.assertEqual(result.status, "cancelled")
        self.assertIsNone(result.late)
        self.assertEqual(result.accepted["a"], 8)
        self.assertEqual(result.unusable["a"], 2)
        self.assertFalse(w.snapshot()["requests"])
        self.assertFalse(w.snapshot()["busy"])

    def test_cold_history_survives_replacement(self):
        w = fixture(cold=True)
        prepare(w)
        w.cold_outage("cold-old", 1000, "v0", 1000)
        w.breakdown("failure", 1000, "v0", False, 86400)
        w.decide("yes", 1100, "request-1", "approve")
        w.advance("transfer", 2400)
        key = next(iter(w.manifest("m")))
        self.assertEqual(w.snapshot()["cold_exposure"][key], 1000)
        w.cold_outage("cold-new", 2500, "v1", 500)
        w.advance("restored", 3000)
        self.assertEqual(w.snapshot()["cold_exposure"][key], 1500)
        self.assertEqual(w.snapshot()["loads"]["auto-1-0"].vehicle_id, "v1")

    def test_combined_replacement_and_reinforcement(self):
        w = fixture()
        prepare(w)
        w.damage_cargo("damage", 1000, "auto-1-0", "a", 2)
        w.breakdown("failure", 1000, "v0", False, 86400)
        w.decide("yes", 1100, "request-1", "approve")
        w.advance("first", 4100)
        w.decide("more", 4100, "request-2", "approve")
        w.advance("complete", 7700)
        self.assertEqual(w.outcome("m", 7700).accepted["a"], 9)
        self.assertEqual(w.outcome("m", 7700).quota_reached_s, 7700)
        self.assertEqual(w.snapshot()["stock"]["origin"]["a"], 9)

    def test_automatic_clocks_independent_of_advance_partition(self):
        def make():
            w = fixture(
                cold=True,
                distance=100,
                policy=IncidentPolicy(seed=0, automatic=True, auto_approve=True),
            )
            # Fix one internal sampled driving clock to exercise the failure path.
            w._drive_left["v0"] = 200
            prepare(w)
            return w

        a, b = make(), make()
        a.advance("all", 20000)
        for t in (1100, 1200, 3000, 5000, 10000, 20000):
            b.advance("part" + str(t), t)
        self.assertEqual(a.outcome("m", 20000), b.outcome("m", 20000))
        self.assertEqual(a.observed_incidents(), b.observed_incidents())
        self.assertTrue(
            any(
                e["kind"] == "mechanical_failure"
                for e in a.observed_incidents()["alerts"]
            )
        )

    def test_rejected_request_can_be_reconsidered_explicitly(self):
        w = fixture()
        prepare(w)
        w.breakdown("failure", 1000, "v0", False, 86400)
        w.decide("no", 1000, "request-1", "reject")
        w.decide("yes", 1100, "request-1", "approve")
        w.advance("done", 4100)
        self.assertEqual(w.outcome("m", 4100).accepted["a"], 10)

    def test_stochastic_supply_repeats_without_future_observation(self):
        a, b = fixture(policy=IncidentPolicy(seed=9)), fixture(
            policy=IncidentPolicy(seed=9)
        )
        for w in (a, b):
            w.stochastic_supply("s", 0, "order", "origin", {"a": 10}, 500)
        self.assertEqual(a.snapshot()["supplies"], b.snapshot()["supplies"])
        self.assertEqual(a.inventory_position("origin", "a"), 10)


if __name__ == "__main__":
    unittest.main()
