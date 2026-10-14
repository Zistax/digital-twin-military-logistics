import unittest
from copy import deepcopy
from dataclasses import asdict, replace
from decimal import Decimal

from src.logistics.cargo_ledger import cargo_events, validate_cargo_ledger
from tests.test_recovery import fixture, prepare


class CargoLedgerTests(unittest.TestCase):
    def setUp(self):
        w = fixture()
        w._vehicles["v1"] = replace(
            w._vehicles["v1"], max_kg=Decimal(4), max_m3=Decimal(4)
        )
        prepare(w)
        w.breakdown("failure", 1000, "v0", False, 86400)
        w.decide("yes", 1100, "request-1", "approve")
        w.advance("done", 20000)
        self.events = cargo_events(w)
        self.deliveries = [asdict(e) for e in w._events]
        self.creations = {
            ("run", "m"): {"observed_s": 0, "features": {"lines": [{"item_id": "a"}]}}
        }
        self.labels = {("run", "m"): {"label_cutoff_s": 20000}}

    def check(self, events):
        return validate_cargo_ledger(
            events, self.deliveries, self.creations, self.labels
        )

    def test_reconstructs_original_load_and_repeated_splits(self):
        self.assertEqual(
            sum(e["quantity"] for e in self.events if e["kind"] == "load"), 10
        )
        self.assertEqual(sum(e["kind"] == "split" for e in self.events), 2)
        self.assertTrue(all(q == 0 for q in self.check(self.events).values()))

    def test_short_load_cannot_fund_deliveries(self):
        events = deepcopy(self.events)
        events[0]["quantity"] = 1
        with self.assertRaises(ValueError):
            self.check(events)

    def test_duplicate_batch_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.check(self.events + [deepcopy(self.events[0])])

    def test_split_before_parent_and_cross_item_rejected(self):
        events = deepcopy(self.events)
        events[1]["at_s"] = 0
        with self.assertRaises(ValueError):
            self.check(events)
        events = deepcopy(self.events)
        events[1]["cargo"][2] = "unknown"
        with self.assertRaises(ValueError):
            self.check(events)


if __name__ == "__main__":
    unittest.main()
