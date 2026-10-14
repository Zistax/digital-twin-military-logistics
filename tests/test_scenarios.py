import unittest
from decimal import Decimal as D

from src.logistics.scenarios import (
    COLD_DEPOTS,
    DEPOTS,
    QUANTITIES,
    SIZES,
    THRESHOLDS,
    ScenarioConfig,
    expected_daily_shipping,
    generate_requests,
    reference_catalog,
)
from src.logistics.scenarios import initialize_scenario, expected_local_withdrawal


class ScenarioTests(unittest.TestCase):
    def test_initialization_shared_stocks_and_reference_fleet(self):
        a, ledger_a = initialize_scenario(ScenarioConfig(seed=9))
        b, ledger_b = initialize_scenario(ScenarioConfig(seed=9, profile="pressure"))
        c, ledger_c = initialize_scenario(ScenarioConfig(seed=9, profile="perturbed"))
        self.assertEqual(ledger_a, ledger_b)
        self.assertEqual(ledger_a, ledger_c)
        self.assertEqual(a.snapshot()["stock"], b.snapshot()["stock"])
        self.assertEqual(a.snapshot()["stock"], c.snapshot()["stock"])
        self.assertEqual(len(a._vehicles), 10)
        self.assertEqual(sum(v.cold for v in a._vehicles.values()), 2)
        self.assertEqual(len(a._network.nodes), 25)
        self.assertFalse(any(row["capacity_limited"] for row in ledger_a))
        a._check()

    def test_local_demand_expectation_includes_rounding(self):
        self.assertEqual(expected_local_withdrawal(D(0)), 0)
        self.assertEqual(expected_local_withdrawal(D(1)), 1)
        self.assertEqual(expected_local_withdrawal(D(10)), D("2.5"))

    def test_catalog_matches_specification(self):
        catalog = {i.item_id: i for i in reference_catalog()}
        self.assertEqual(len(catalog), 15)
        self.assertEqual(catalog["spares-large"].kg, D(50))
        self.assertEqual(catalog["electronics-large"].m3, D(".25"))
        self.assertEqual(catalog["cold-small"].m3, D(".025"))
        self.assertEqual(sum(i.cold for i in catalog.values()), 3)
        for item in catalog.values():
            self.assertEqual(
                item.handling_s, (30, 60, 120)[SIZES.index(item.item_id.split("-")[1])]
            )

    def test_reproducible_demand_and_profile_pairing(self):
        regular = generate_requests(ScenarioConfig(seed=42))
        self.assertEqual(regular, generate_requests(ScenarioConfig(seed=42)))
        self.assertEqual(
            regular, generate_requests(ScenarioConfig(seed=42, profile="perturbed"))
        )
        self.assertNotEqual(regular, generate_requests(ScenarioConfig(seed=43)))

    def test_pressure_only_increases_arrival_rate(self):
        regular = generate_requests(ScenarioConfig(seed=7))
        pressure = generate_requests(ScenarioConfig(seed=7, profile="pressure"))
        self.assertGreater(len(pressure), len(regular))
        for a, b in zip(regular, pressure):
            self.assertLessEqual(abs(a.start_s - 2 * b.start_s), 1)
            self.assertEqual(
                (a.lines, a.urgent, a.origin_id, a.destination_id, a.deadline_margin),
                (b.lines, b.urgent, b.origin_id, b.destination_id, b.deadline_margin),
            )

    def test_constraints_over_multiple_seeds(self):
        for seed in range(10):
            requests = generate_requests(ScenarioConfig(seed=seed))
            self.assertEqual(len({r.request_id for r in requests}), len(requests))
            self.assertEqual(
                [r.start_s for r in requests], sorted(r.start_s for r in requests)
            )
            for r in requests:
                self.assertLess(r.start_s, 7 * 86400)
                self.assertNotEqual(r.origin_id, r.destination_id)
                self.assertTrue({r.origin_id, r.destination_id} <= set(DEPOTS))
                self.assertEqual(len({line.item_id for line in r.lines}), len(r.lines))
                for line in r.lines:
                    category, size = line.item_id.split("-")
                    lo, hi = QUANTITIES[SIZES.index(size)]
                    self.assertTrue(lo <= line.requested <= hi)
                    self.assertEqual(line.threshold, THRESHOLDS[category])
                    if category == "cold":
                        self.assertTrue({r.origin_id, r.destination_id} <= COLD_DEPOTS)

    def test_deadline_margins_in_declared_ranges(self):
        ranges = {
            "tight": (D(1), D("1.2")),
            "ordinary": (D("1.3"), D("1.6")),
            "wide": (D("1.8"), D("2.2")),
        }
        for r in generate_requests(ScenarioConfig(seed=5)):
            lo, hi = ranges[r.deadline_kind]
            self.assertTrue(lo <= r.deadline_margin <= hi)
            self.assertFalse(hasattr(r, "deadline_s"))

    def test_horizon_and_invalid_configuration(self):
        config = ScenarioConfig(generation_days=2, extension_days=3)
        self.assertEqual(config.stop_s, 5 * 86400)
        self.assertTrue(all(r.start_s < 2 * 86400 for r in generate_requests(config)))
        for kwargs in (
            {"seed": -1},
            {"seed": True},
            {"profile": "unknown"},
            {"generation_days": 0},
            {"extension_days": -1},
        ):
            with self.assertRaises(ValueError):
                ScenarioConfig(**kwargs)

    def test_initial_stock_demand_is_analytic_and_cold_compatible(self):
        demand = expected_daily_shipping()
        self.assertEqual(demand, expected_daily_shipping())
        self.assertEqual(demand["local-b"]["cold-small"], 0)
        self.assertEqual(demand["central-a"], demand["central-b"])
        self.assertGreater(demand["central-a"]["cold-small"], 0)
        # Four equally likely destinations, two with all five categories.
        expected = D(".5") * (2 * D(".6") + 2 * D(".625")) * D(40)
        self.assertAlmostEqual(demand["central-a"]["food-small"], expected)


if __name__ == "__main__":
    unittest.main()
