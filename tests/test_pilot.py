import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.logistics.pilot import run_pilot
from tests.test_dataset import run


class PilotTests(unittest.TestCase):
    def test_invalid_plan_does_not_create_report_directory(self):
        with TemporaryDirectory() as root:
            path = Path(root) / "pilot"
            for seeds in ((), (0, 0), (-1,), (True,)):
                with self.assertRaises(ValueError):
                    run_pilot(path, seeds)
                self.assertFalse(path.exists())

    def test_diagnostics_account_for_completed_and_blocked_missions(self):
        completed = run()
        self.assertEqual(
            completed["diagnostics"]["mission_statuses"], {"logistics_complete": 1}
        )
        self.assertEqual(completed["diagnostics"]["open_missions"], [])
        blocked = run(0)
        row = blocked["diagnostics"]["open_missions"][0]
        self.assertEqual(row["status"], "waiting")
        self.assertEqual(row["missing_reservation_units"], 10)
        self.assertEqual(blocked["diagnostics"]["peak_sampled"]["open_missions"], 1)


if __name__ == "__main__":
    unittest.main()
