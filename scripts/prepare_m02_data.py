"""Verify and sample native rolling tables without loading final-test tables."""

import argparse
from collections import defaultdict
import hashlib
import heapq
import gzip
import json
from pathlib import Path
import sys
import shutil
import zipfile

from prepare_m01_data import ARCHIVE_SHA256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from logistics.initial_prediction import load_creation  # noqa: E402
from logistics.rolling_prediction import rolling_features  # noqa: E402


def sample_observations(lines):
    """Bounded sampling by observable IDs/state; labels cannot affect selection."""
    buckets, first, count = defaultdict(list), {}, 0
    digest = hashlib.sha256()
    for raw in lines:
        digest.update(raw)
        obs = json.loads(raw)
        count += 1
        regime = "pre" if obs["features"]["seconds_to_deadline"] > 0 else "post"
        key = (obs["mission_id"], regime)
        rank = int.from_bytes(
            hashlib.sha256(("m02-v1|" + obs["observation_id"]).encode()).digest(), "big"
        )
        bucket = buckets[key]
        entry = (-rank, obs["observation_id"], obs)
        if len(bucket) < 4:
            heapq.heappush(bucket, entry)
        elif rank < -bucket[0][0]:
            heapq.heapreplace(bucket, entry)
        phase = (*key, obs["features"]["status"])
        previous = first.get(phase)
        if previous is None or obs["observed_s"] < previous["observed_s"]:
            first[phase] = obs
    selected = {
        o["observation_id"]: o for bucket in buckets.values() for _, _, o in bucket
    }
    selected.update({o["observation_id"]: o for o in first.values()})
    return selected, count, digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    protocol = Path(__file__).resolve().parents[1] / "docs/protocollo-m02-v1.md"
    rows, _ = load_creation(args.dataset)
    creations = {tuple(r["key"]): r for r in rows}
    split = json.loads((args.dataset / "split_manifest.json").read_text())
    accepted = {
        r["bundle"]: r for s in ("training", "calibration") for r in split["sets"][s]
    }
    seen, provenance, counts = set(), [], defaultdict(int)
    path = args.output / "sampled.jsonl.gz"
    temporary = path.with_suffix(".jsonl.tmp")
    with temporary.open("w") as out:
        for i, expected in enumerate(ARCHIVE_SHA256, 1):
            archive_path = args.archives / f"Dataset_D03_Parte_{i}_di_4.zip"
            with archive_path.open("rb") as source:
                if hashlib.file_digest(source, "sha256").hexdigest() != expected:
                    raise ValueError("archive checksum mismatch")
            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())
                for folder, record in accepted.items():
                    prefix = "d03-batch-v1/" + folder + "/"
                    if prefix + "manifest.json" not in names:
                        continue
                    manifest_bytes = archive.read(prefix + "manifest.json")
                    if (
                        hashlib.sha256(manifest_bytes).hexdigest()
                        != record["manifest_sha256"]
                    ):
                        raise ValueError("manifest checksum mismatch")
                    manifest = json.loads(manifest_bytes)
                    with archive.open(prefix + "rolling_observations.jsonl") as source:
                        sampled, count, sha = sample_observations(source)
                    meta = manifest["files"]["rolling_observations.jsonl"]
                    if (count, sha) != (meta["rows"], meta["sha256"]):
                        raise ValueError("observation checksum/count mismatch")
                    digest, targets, n = hashlib.sha256(), {}, 0
                    with archive.open(prefix + "rolling_targets.jsonl") as source:
                        for raw in source:
                            digest.update(raw)
                            target = json.loads(raw)
                            n += 1
                            if target["observation_id"] in sampled:
                                if target["observation_id"] in targets:
                                    raise ValueError("duplicate target")
                                targets[target["observation_id"]] = target
                    meta = manifest["files"]["rolling_targets.jsonl"]
                    if (n, digest.hexdigest()) != (meta["rows"], meta["sha256"]):
                        raise ValueError("target checksum/count mismatch")
                    if sampled.keys() != targets.keys():
                        raise ValueError("unpaired rolling target")
                    for oid, obs in sorted(sampled.items()):
                        target = targets[oid]
                        key = (obs["simulation_id"], obs["mission_id"])
                        original = creations[key]
                        x = rolling_features(original["observation"], obs)
                        if any(
                            target[k] != obs[k]
                            for k in ("simulation_id", "mission_id", "observation_id")
                        ):
                            raise ValueError("target identity mismatch")
                        expected_kind = (
                            "delay_if_late"
                            if x["regime"] == "pre"
                            else "remaining_after_deadline"
                        )
                        if (
                            target["target_kind"] != expected_kind
                            or target["label_cutoff_s"] < obs["observed_s"]
                        ):
                            raise ValueError("target regime/cutoff mismatch")
                        row = {
                            "key": list(key),
                            "group": record["group_id"],
                            "split": record["split"],
                            "profile": record["profile"],
                            "observation": obs,
                            "creation": original["observation"],
                            "target": target,
                            "x": x,
                        }
                        out.write(json.dumps(row, allow_nan=False) + "\n")
                    counts[record["split"]] += len(sampled)
                    provenance.append(
                        {
                            "simulation_id": record["simulation_id"],
                            "group": record["group_id"],
                            "split": record["split"],
                            "native_snapshots": count,
                            "sampled_snapshots": len(sampled),
                            "files": {
                                k: manifest["files"][k]
                                for k in (
                                    "rolling_observations.jsonl",
                                    "rolling_targets.jsonl",
                                )
                            },
                        }
                    )
                    seen.add(folder)
                    print(
                        json.dumps(
                            {
                                "bundles": len(seen),
                                "run": record["simulation_id"],
                                "sampled": len(sampled),
                            }
                        ),
                        flush=True,
                    )
    if seen != set(accepted):
        raise ValueError("missing development bundles")
    with temporary.open("rb") as source, path.open("wb") as destination:
        with gzip.GzipFile(fileobj=destination, mode="wb", mtime=0) as compressed:
            shutil.copyfileobj(source, compressed)
    temporary.unlink()
    metadata = {
        "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": dict(counts),
        "test_tables_read": 0,
        "provenance": provenance,
    }
    (args.output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
