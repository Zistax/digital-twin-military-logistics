import json
import unittest
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from src.logistics.bundles import read_verified_bundle
from src.logistics.dataset import export_creation_dataset
from tests.test_rolling_dataset import result


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "bundle"
        export_creation_dataset(result(), self.root)

    def rewrite(self, name, rows):
        data = "".join(json.dumps(row) + "\n" for row in rows).encode()
        (self.root / name).write_bytes(data)
        manifest = json.loads((self.root / "manifest.json").read_text())
        manifest["files"][name] = {
            "rows": len(rows),
            "sha256": sha256(data).hexdigest(),
        }
        (self.root / "manifest.json").write_text(json.dumps(manifest))

    def test_roundtrip(self):
        bundle = read_verified_bundle(self.root)
        self.assertEqual(len(bundle["tables"]["rolling_targets.jsonl"]), 3)
        self.assertEqual(bundle["manifest"]["group_id"], "base-seed-0")

    def test_plausible_quantity_without_delivery_is_rejected(self):
        rows = [
            json.loads(line)
            for line in (self.root / "rolling_observations.jsonl")
            .read_text()
            .splitlines()
        ]
        rows[0]["features"]["lines"][0]["accepted"] = 1
        self.rewrite("rolling_observations.jsonl", rows)
        with self.assertRaisesRegex(ValueError, "unsupported by observed delivery"):
            read_verified_bundle(self.root)

    def test_missing_delivery_cannot_support_final_quota(self):
        self.rewrite("delivery_events.jsonl", [])
        with self.assertRaisesRegex(ValueError, "quota time unsupported"):
            read_verified_bundle(self.root)

    def test_rolling_feature_tampering_rejected_after_rehash(self):
        from copy import deepcopy

        original = [
            json.loads(line)
            for line in (self.root / "rolling_observations.jsonl")
            .read_text()
            .splitlines()
        ]
        for mutation in (
            lambda r: r["features"].update(hidden_bad=4),
            lambda r: r["features"].update(elapsed_s=999),
            lambda r: r["features"]["lines"].clear(),
            lambda r: r["features"]["lines"][0].update(accepted=-1),
        ):
            rows = deepcopy(original)
            mutation(rows[0])
            self.rewrite("rolling_observations.jsonl", rows)
            with self.assertRaises(ValueError):
                read_verified_bundle(self.root)

    def test_fabricated_final_delay_rejected_after_rehash(self):
        rows = [
            json.loads(line)
            for line in (self.root / "labels.jsonl").read_text().splitlines()
        ]
        rows[0]["delay_minutes"] = 999
        self.rewrite("labels.jsonl", rows)
        with self.assertRaisesRegex(ValueError, "delay"):
            read_verified_bundle(self.root)

    def test_inconsistent_censoring_rejected_after_rehash(self):
        rows = [
            json.loads(line)
            for line in (self.root / "labels.jsonl").read_text().splitlines()
        ]
        rows[0]["quota_censored"] = True
        self.rewrite("labels.jsonl", rows)
        with self.assertRaisesRegex(ValueError, "censoring"):
            read_verified_bundle(self.root)

    def test_invented_remaining_target_rejected_after_rehash(self):
        rows = [
            json.loads(line)
            for line in (self.root / "rolling_targets.jsonl").read_text().splitlines()
        ]
        rows[-1]["target_minutes"] = 0
        self.rewrite("rolling_targets.jsonl", rows)
        with self.assertRaisesRegex(ValueError, "target inconsistent"):
            read_verified_bundle(self.root)

    def test_changed_bytes_block_read(self):
        with (self.root / "labels.jsonl").open("ab") as file:
            file.write(b" ")
        with self.assertRaisesRegex(ValueError, "checksum"):
            read_verified_bundle(self.root)

    def test_missing_file_blocks_read(self):
        (self.root / "labels.jsonl").unlink()
        with self.assertRaises(ValueError):
            read_verified_bundle(self.root)

    def test_recomputed_checksum_does_not_hide_orphan(self):
        rows = [
            json.loads(line)
            for line in (self.root / "labels.jsonl").read_text().splitlines()
        ]
        rows[0]["mission_id"] = "other"
        self.rewrite("labels.jsonl", rows)
        with self.assertRaisesRegex(ValueError, "references"):
            read_verified_bundle(self.root)

    def test_weight_change_and_duplicate_block_read(self):
        rows = [
            json.loads(line)
            for line in (self.root / "rolling_targets.jsonl").read_text().splitlines()
        ]
        rows[0]["sample_weight"] = 1
        self.rewrite("rolling_targets.jsonl", rows)
        with self.assertRaisesRegex(ValueError, "weights"):
            read_verified_bundle(self.root)
        self.rewrite("rolling_targets.jsonl", rows + [rows[0]])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            read_verified_bundle(self.root)

    def test_manifest_cannot_select_arbitrary_files(self):
        path = self.root / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["files"]["../other"] = manifest["files"].pop("labels.jsonl")
        path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            read_verified_bundle(self.root)


if __name__ == "__main__":
    unittest.main()
