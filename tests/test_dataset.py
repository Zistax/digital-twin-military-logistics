import unittest
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from src.logistics.dataset import build_creation_dataset, export_creation_dataset
from src.logistics.experiments import run_experiment
from src.logistics.scenarios import ScenarioConfig
from tests.test_estimates import request
from tests.test_recovery import fixture


def run(stock=20):
    w = fixture()
    if stock:
        w.receive("stock", 0, "origin", {"a": stock})
    return run_experiment(
        ScenarioConfig(generation_days=1, extension_days=0),
        warehouse=w,
        requests=[request()],
    )


class DatasetTests(unittest.TestCase):
    def test_creation_state_is_preserved_after_delivery(self):
        result = run()
        dataset = build_creation_dataset(result)
        line = dataset["observations"][0]["features"]["lines"][0]
        self.assertEqual(line["available_origin"], 20)
        self.assertEqual(line["stock_destination"], 0)
        self.assertEqual(result["outcomes"]["new"]["accepted"]["a"], 10)
        self.assertEqual(dataset["kpi"]["quota_reached"], 1)
        self.assertEqual(dataset["kpi"]["on_time_reached"], 1)
        self.assertNotIn("late", dataset["observations"][0]["features"])

    def test_censored_delay_remains_null(self):
        dataset = build_creation_dataset(run(0))
        self.assertIsNone(dataset["labels"][0]["delay_minutes"])
        self.assertTrue(dataset["labels"][0]["quota_censored"])
        self.assertIsNone(dataset["kpi"]["mean_delay_reached_minutes"])

    def test_future_feature_and_cutoff_are_blocked(self):
        result = run()
        result["observations"][0]["features"]["hidden_bad"] = 0
        with self.assertRaises(ValueError):
            build_creation_dataset(result)
        result = run()
        result["observations"][0]["observed_s"] += 1
        with self.assertRaises(ValueError):
            build_creation_dataset(result)

    def test_duplicates_and_orphans(self):
        result = run()
        result["observations"].append(deepcopy(result["observations"][0]))
        self.assertEqual(len(build_creation_dataset(result)["observations"]), 1)
        result["observations"][1]["features"]["free_vehicles"] = 0
        with self.assertRaises(ValueError):
            build_creation_dataset(result)
        result = run()
        result["outcomes"] = {}
        with self.assertRaises(ValueError):
            build_creation_dataset(result)

    def test_export_is_reproducible_and_does_not_overwrite(self):
        result = run()
        with TemporaryDirectory() as root:
            a, b = Path(root) / "a", Path(root) / "b"
            manifest = export_creation_dataset(result, a)
            self.assertEqual(manifest, export_creation_dataset(result, b))
            for name, description in manifest["files"].items():
                self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
                self.assertEqual(
                    sha256((a / name).read_bytes()).hexdigest(), description["sha256"]
                )
            with self.assertRaises(FileExistsError):
                export_creation_dataset(result, a)

    def test_fabricated_final_delay_blocks_export(self):
        result = run(0)
        result["outcomes"]["new"]["delay_minutes"] = 0
        with self.assertRaises(ValueError):
            build_creation_dataset(result)


if __name__ == "__main__":
    unittest.main()
