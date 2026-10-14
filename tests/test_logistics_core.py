import unittest
from dataclasses import replace
from decimal import Decimal
from src.logistics.core import MissionLine, replay
from src.logistics.demo import reference_case


class LogisticsTests(unittest.TestCase):
    def setUp(self):
        self.m, self.loads, self.events = reference_case()

    def run_at(self, t):
        return replay(self.m, self.loads, self.events, t)

    def test_reference_and_conservation(self):
        r = self.run_at(5700)
        self.assertEqual(r.delay_minutes, 35)
        self.assertFalse(r.logistics_complete)
        final = self.run_at(6000)
        self.assertTrue(final.logistics_complete)
        self.assertEqual(final.delay_minutes, 35)
        for item in final.accepted:
            initial = sum(q for (_, _, i), q in self.loads.items() if i == item)
            self.assertEqual(
                initial,
                final.accepted[item] + final.onboard[item] + final.unusable[item],
            )

    def test_exact_deadline_between_ticks(self):
        self.m = replace(self.m, deadline_s=5701)
        self.events[1] = replace(self.events[1], occurred_s=5701, observed_s=5701)
        self.assertFalse(self.run_at(5701).late)
        self.assertEqual(self.run_at(5701).delay_minutes, 0)
        self.assertIsNone(self.run_at(5700).late)

    def test_censoring(self):
        self.assertIsNone(self.run_at(3599).late)
        self.assertTrue(self.run_at(3600).late)
        self.assertIsNone(self.run_at(3600).delay_minutes)

    def test_no_compensation_and_damage(self):
        self.assertEqual(self.m.lines[1].minimum, 5)
        self.events[0] = replace(self.events[0], accepted=10)
        self.events[1] = replace(self.events[1], accepted=4, unusable=1)
        self.events = self.events[:2]
        r = self.run_at(6000)
        self.assertEqual(r.status, "incomplete")
        self.assertTrue(r.logistics_complete)
        self.assertEqual(r.unusable["spares-large"], 1)

    def test_idempotence_and_reordering(self):
        expected = self.run_at(6000)
        self.events = list(reversed(self.events)) + self.events
        self.assertEqual(self.run_at(6000), expected)

    def test_duplicate_conflict(self):
        self.events.append(replace(self.events[0], accepted=8))
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.run_at(6000)

    def test_double_unload(self):
        self.events.append(replace(self.events[0], event_id="retry"))
        with self.assertRaisesRegex(ValueError, "conservation"):
            self.run_at(6000)

    def test_no_future_leakage(self):
        expected = self.run_at(3600)
        self.events[1] = replace(self.events[1], occurred_s=3300, observed_s=5700)
        self.assertEqual(self.run_at(3600), expected)
        self.assertEqual(self.run_at(5700).quota_reached_s, 5700)

    def test_invalid_contracts(self):
        for field, value in [
            ("accepted", -1),
            ("accepted", True),
            ("observed_s", 2999),
            ("schema_version", 2),
        ]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                replace(self.events[0], **{field: value})
        for threshold in [Decimal("NaN"), Decimal("0"), Decimal("1.1"), 0.9]:
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                MissionLine("a", 1, threshold)
        for change in [
            {"deadline_s": 0},
            {"destination_id": "central-a"},
            {"lines": ()},
            {"lines": self.m.lines * 2},
        ]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.m, **change)

    def test_foreign_event_and_missing_cargo(self):
        self.events[0] = replace(self.events[0], mission_id="other")
        with self.assertRaisesRegex(ValueError, "another mission"):
            self.run_at(6000)
        self.events = reference_case()[2]
        self.loads = {}
        with self.assertRaisesRegex(ValueError, "unknown cargo"):
            self.run_at(6000)


if __name__ == "__main__":
    unittest.main()
