"""Restore lost bundle bytes only if regeneration matches every frozen checksum."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

import src.logistics.experiments as engine
from src.logistics.batch import source_hashes
from src.logistics.dataset import build_creation_dataset
from src.logistics.journal import replay_journal
from src.logistics.rolling import build_rolling_dataset
from src.logistics.scenarios import ScenarioConfig


def digest(path):
    value = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def write_rows(path, rows):
    count = 0
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            count += 1
    return count


def restore(root, simulation_id):
    root = root.resolve()
    records = [
        json.loads(p.read_text())
        for p in (root / "records").glob(f"{simulation_id}-attempt-*.json")
    ]
    accepted = [r for r in records if r.get("valid") is True]
    if len(accepted) != 1:
        raise ValueError("one frozen accepted record required")
    record = accepted[0]
    plan = json.loads((root / "plan.json").read_text())
    if source_hashes() != plan["source_sha256"]:
        raise ValueError("source version changed")
    bundle = root / record["bundle"]
    manifest = json.loads((bundle / "manifest.json").read_text())
    if digest(bundle / "manifest.json") != record["manifest_sha256"]:
        raise ValueError("manifest changed; cannot restore against it")
    evidence_dir = root / "storage-repairs" / simulation_id
    evidence_dir.mkdir(parents=True, exist_ok=False)
    with TemporaryDirectory(prefix="d03-restore-") as temporary:
        work = Path(temporary)
        original = engine.observation_context
        context_count = 0
        with (work / "planning_contexts.jsonl").open("w") as contexts:

            def stream_context(w, observation):
                nonlocal context_count
                value = original(w, observation)
                contexts.write(
                    json.dumps(value, sort_keys=True, allow_nan=False) + "\n"
                )
                context_count += 1
                return {}

            engine.observation_context = stream_context
            try:
                result = engine.run_experiment(
                    ScenarioConfig(**manifest["config"]),
                    engine.RunPolicy(**manifest["run_manifest"]["runner"]),
                    capture_trace=True,
                )
            finally:
                engine.observation_context = original
        if result["run_manifest"] != manifest["run_manifest"]:
            raise ValueError("regeneration provenance mismatch")
        creation = build_creation_dataset(result)
        rolling = build_rolling_dataset(result)
        rows = {
            "observations.jsonl": creation["observations"],
            "labels.jsonl": creation["labels"],
            "rolling_observations.jsonl": rolling["observations"],
            "rolling_targets.jsonl": rolling["targets"],
            "delivery_events.jsonl": result["delivery_events"],
            "cargo_events.jsonl": result["cargo_events"],
            "operational_events.jsonl": result["operational_events"],
        }
        counts = {
            name: write_rows(work / name, values) for name, values in rows.items()
        }
        counts["planning_contexts.jsonl"] = context_count
        replay_journal(result["operational_events"], simulation_id, result["stopped_s"])
        checks = {}
        for name, info in manifest["files"].items():
            checks[name] = (
                digest(work / name) == info["sha256"] and counts[name] == info["rows"]
            )
        trace = work / "trace.jsonl"
        write_rows(trace, result["operational_trace"])
        checks["trace"] = digest(trace) == record["trace_sha256"]
        if not all(checks.values()) or creation["kpi"] != manifest["kpi"]:
            (evidence_dir / "rejected-regeneration.json").write_text(
                json.dumps(checks, indent=2)
            )
            raise ValueError(
                "regeneration differs; original checksums will not be changed"
            )
        restored = []
        for name, info in manifest["files"].items():
            target = bundle / name
            if not target.exists() or digest(target) != info["sha256"]:
                if target.exists():
                    shutil.copy2(target, evidence_dir / f"{name}.damaged")
                staged = bundle / f"{name}.restore"
                shutil.copyfile(work / name, staged)
                if digest(staged) != info["sha256"]:
                    raise ValueError("restoration copy checksum failed")
                staged.replace(target)
                restored.append(name)
        evidence = {
            "restored_utc": datetime.now(timezone.utc).isoformat(),
            "simulation_id": simulation_id,
            "restored_files": restored,
            "all_eight_tables_and_trace_match_original": all(checks.values()),
            "checksums_and_manifest_unchanged": True,
            "checks": checks,
        }
        (evidence_dir / "restoration.json").write_text(json.dumps(evidence, indent=2))
        print(json.dumps(evidence), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    parser.add_argument("simulation_id")
    args = parser.parse_args()
    restore(args.batch, args.simulation_id)
