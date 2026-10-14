import unittest
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.logistics.journal import replay_journal
from src.logistics.provenance import validate_manifest
from src.logistics.dataset import export_creation_dataset
from src.logistics.bundles import read_verified_bundle
from src.logistics.table_import import import_table
from tests.test_dataset import run


class JournalContractTests(unittest.TestCase):
    def test_replay_conserves_physical_stock_and_reconstructs_history(self):
        result = run()
        state = replay_journal(result["operational_events"], "run", result["stopped_s"])
        self.assertEqual(state["stock"]["origin"]["a"], 10)
        self.assertEqual(state["stock"]["dest"]["a"], 10)
        early = replay_journal(result["operational_events"], "run", 1000)
        self.assertEqual(early["stock"]["dest"].get("a", 0), 0)
        tampered = deepcopy(result["operational_events"])
        tampered[0]["changes"]["stock"]["origin"]["a"] += 1
        with self.assertRaises(ValueError):
            replay_journal(tampered, "run", result["stopped_s"])

    def test_configuration_manifest_detects_changes(self):
        result = run()
        validate_manifest(result["run_manifest"], result["config"])
        bad = deepcopy(result["run_manifest"])
        bad["catalog"][0]["kg"] = "999"
        with self.assertRaises(ValueError):
            validate_manifest(bad, result["config"])

    def test_every_table_import_roundtrips_and_quarantines_exact_threshold(self):
        result = run()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bundle"
            export_creation_dataset(result, path)
            bundle = read_verified_bundle(path)
            for name, rows in bundle["tables"].items():
                text = "\n".join(json.dumps(row) for row in rows)
                imported = import_table(text, name, bundle)
                self.assertFalse(imported["blocked"], (name, imported["critical"]))
            row = json.dumps(bundle["tables"]["labels.jsonl"][0])
            imported = import_table(
                "\n".join([row] * 199 + ["broken"]), "labels.jsonl", bundle
            )
            self.assertFalse(imported["blocked"])
            self.assertEqual(imported["invalid_rows"], 1)

    def test_critical_import_change_blocks_even_with_valid_json(self):
        result = run()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bundle"
            export_creation_dataset(result, path)
            bundle = read_verified_bundle(path)
            rows = deepcopy(bundle["tables"]["labels.jsonl"])
            rows[0]["delay_minutes"] = 999
            imported = import_table(
                "\n".join(json.dumps(row) for row in rows), "labels.jsonl", bundle
            )
            self.assertTrue(imported["blocked"])
            self.assertEqual(imported["records"], [])

    def test_hidden_future_context_is_rejected(self):
        from src.logistics.context import validate_context

        result = run()
        row = deepcopy(result["planning_contexts"][0])
        row["context"]["fleet"]["v0"]["future_failure_s"] = 123
        with self.assertRaises(ValueError):
            validate_context(row, result["observations"][0])


if __name__ == "__main__":
    unittest.main()
