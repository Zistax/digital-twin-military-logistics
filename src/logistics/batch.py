"""Frozen, resumable D03 dataset production with paired group splits."""

from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
import traceback

from .bundles import read_verified_bundle
from .dataset import build_creation_dataset, export_creation_dataset
from .experiments import run_experiment
from .scenarios import ScenarioConfig
from .training_masks import creation_masks, rolling_masks

PROFILES = ("regular", "pressure", "perturbed")
SPLIT_COUNTS = {"training": 18, "calibration": 6, "test": 6}
DEVELOPMENT_SEEDS = (0, 1, 2, 3)


def source_hashes():
    return {
        p.name: sha256(p.read_bytes()).hexdigest()
        for p in sorted(Path(__file__).parent.glob("*.py"))
    }


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    temporary.replace(path)


def digest(value):
    return sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def make_plan():
    seeds = list(range(1000, 1030))
    # Outcome-independent assignment; freeze before the first generated mission.
    ranked = sorted(
        seeds, key=lambda seed: sha256(f"d03-split-v1|{seed}".encode()).digest()
    )
    groups = []
    offset = 0
    for split, count in SPLIT_COUNTS.items():
        for seed in ranked[offset : offset + count]:
            groups.append(
                {"seed": seed, "group_id": f"base-seed-{seed}", "split": split}
            )
        offset += count
    plan = {
        "plan_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "generation_days": 7,
        "extension_days": 7,
        "development_seeds_excluded": list(DEVELOPMENT_SEEDS),
        "assignment": "SHA256(d03-split-v1|seed), 18/6/6 paired seed groups",
        "groups": groups,
        "runs": [
            {
                **group,
                "profile": profile,
                "simulation_id": f"scenario-{group['seed']}-{profile}",
            }
            for group in groups
            for profile in PROFILES
        ],
        "source_sha256": source_hashes(),
        "test_usage": (
            "Integrity and descriptive counts only; no model/threshold selection"
        ),
        "invalid_policy": (
            "Keep failed attempts; retry same frozen seed, never silently replace"
        ),
    }
    plan["plan_sha256"] = digest(plan)
    validate_plan(plan)
    return plan


def validate_plan(plan):
    unsigned = {k: v for k, v in plan.items() if k != "plan_sha256"}
    if digest(unsigned) != plan["plan_sha256"] or plan["plan_version"] != 1:
        raise ValueError("plan checksum/version mismatch")
    if (plan["generation_days"], plan["extension_days"]) != (7, 7):
        raise ValueError("D03 requires the frozen 7+7-day horizon")
    groups = {g["seed"]: g for g in plan["groups"]}
    if len(groups) != 30 or len(plan["groups"]) != 30:
        raise ValueError("30 distinct paired seed groups required")
    if Counter(g["split"] for g in groups.values()) != Counter(SPLIT_COUNTS):
        raise ValueError("group split counts mismatch")
    if set(groups) & set(DEVELOPMENT_SEEDS) or plan[
        "development_seeds_excluded"
    ] != list(DEVELOPMENT_SEEDS):
        raise ValueError("development seed leakage")
    expected = set()
    for seed, group in groups.items():
        ScenarioConfig(seed)
        if group["group_id"] != f"base-seed-{seed}":
            raise ValueError("invalid seed group identity")
        expected.update((seed, profile) for profile in PROFILES)
    actual = [(row["seed"], row["profile"]) for row in plan["runs"]]
    if len(actual) != 90 or set(actual) != expected:
        raise ValueError("missing or repeated seed/profile run")
    for row in plan["runs"]:
        if any(row[k] != groups[row["seed"]][k] for k in ("group_id", "split")):
            raise ValueError("paired group crosses splits")
        if row["simulation_id"] != f"scenario-{row['seed']}-{row['profile']}":
            raise ValueError("simulation identity mismatch")


def verify_bundle(bundle, row, plan):
    manifest = bundle["manifest"]
    config = ScenarioConfig(
        row["seed"], row["profile"], plan["generation_days"], plan["extension_days"]
    )
    if manifest["schema_version"] != 4 or manifest["group_id"] != row["group_id"]:
        raise ValueError("batch bundle version/group mismatch")
    if manifest["config"] != config.__dict__:
        raise ValueError("batch scenario configuration mismatch")
    provenance = manifest["run_manifest"]
    if (
        provenance["simulation_id"] != row["simulation_id"]
        or provenance["source_sha256"] != plan["source_sha256"]
    ):
        raise ValueError("batch source or simulation identity mismatch")
    for rows in bundle["tables"].values():
        if any(value["simulation_id"] != row["simulation_id"] for value in rows):
            raise ValueError("cross-simulation data contamination")


def table_counts(bundle):
    labels = bundle["tables"]["labels.jsonl"]
    targets = bundle["tables"]["rolling_targets.jsonl"]
    masks = Counter()
    for row in labels:
        masks.update(k for k, enabled in creation_masks(row).items() if enabled)
    rolling = Counter()
    for row in targets:
        rolling.update(k for k, enabled in rolling_masks(row).items() if enabled)
    return {
        "rows": {name: len(rows) for name, rows in bundle["tables"].items()},
        "creation_training_eligibility": dict(masks),
        "rolling_training_eligibility": dict(rolling),
    }


def execute_run(payload):
    root_text, row, plan, attempt = payload
    root = Path(root_text)
    name = row["simulation_id"]
    started = perf_counter()
    record = {**row, "attempt": attempt, "plan_sha256": plan["plan_sha256"]}
    try:
        if source_hashes() != plan["source_sha256"]:
            raise ValueError("source changed after plan freeze")
        result = run_experiment(
            ScenarioConfig(row["seed"], row["profile"], 7, 7), capture_trace=True
        )
        path = root / "bundles" / f"{name}-attempt-{attempt}"
        export_creation_dataset(result, path)
        bundle = read_verified_bundle(path)
        verify_bundle(bundle, row, plan)
        data = build_creation_dataset(result)
        trace_path = root / "traces" / f"{name}-attempt-{attempt}.jsonl"
        trace = "".join(
            json.dumps(value, sort_keys=True, allow_nan=False) + "\n"
            for value in result["operational_trace"]
        )
        trace_path.write_bytes(trace.encode("utf-8"))
        unexplained = [
            mid
            for mid, reasons in result["diagnostics"]["terminal_blockers"].items()
            if not reasons
        ]
        if unexplained or not result["operational_trace"]:
            raise ValueError("missing trace or unexplained open mission")
        if source_hashes() != plan["source_sha256"]:
            raise ValueError("source changed during run")
        record.update(
            {
                "valid": True,
                "bundle": str(path.relative_to(root)),
                "manifest_sha256": sha256(
                    (path / "manifest.json").read_bytes()
                ).hexdigest(),
                "trace": str(trace_path.relative_to(root)),
                "trace_sha256": sha256(trace.encode()).hexdigest(),
                "kpi": data["kpi"],
                "stopped_s": result["stopped_s"],
                "stop_reason": result["stop_reason"],
                "unexplained_open_missions": unexplained,
                **table_counts(bundle),
            }
        )
    except Exception as error:
        record.update(
            {
                "valid": False,
                "error_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
            }
        )
    record["wall_seconds"] = round(perf_counter() - started, 3)
    write_json(root / "records" / f"{name}-attempt-{attempt}.json", record)
    return record


def audit_record(payload):
    root_text, row, plan, record = payload
    root = Path(root_text)
    if record.get("valid") is not True or record["plan_sha256"] != plan["plan_sha256"]:
        raise ValueError("invalid run record")
    path = root / record["bundle"]
    if (
        sha256((path / "manifest.json").read_bytes()).hexdigest()
        != record["manifest_sha256"]
    ):
        raise ValueError("run manifest changed after verification")
    bundle = read_verified_bundle(path)
    verify_bundle(bundle, row, plan)
    if table_counts(bundle) != {k: record[k] for k in table_counts(bundle)}:
        raise ValueError("stored table counts or training masks mismatch")
    if record["kpi"] != bundle["manifest"]["kpi"]:
        raise ValueError("stored KPI mismatch")
    if (
        sha256((root / record["trace"]).read_bytes()).hexdigest()
        != record["trace_sha256"]
    ):
        raise ValueError("operational trace changed")
    return record


def summarize(plan, records):
    validate_plan(plan)
    expected = {(r["seed"], r["profile"]): r for r in plan["runs"]}
    identities = [(r["seed"], r["profile"]) for r in records]
    if len(records) != 90 or set(identities) != set(expected):
        raise ValueError("90 unique verified runs required")
    totals = {"all": Counter()}
    counts = Counter()
    for record in records:
        row = expected[(record["seed"], record["profile"])]
        if record["valid"] is not True or any(record[k] != row[k] for k in row):
            raise ValueError("invalid membership record")
        kpi = record["kpi"]
        if (
            kpi["missions"]
            != kpi["quota_reached"] + kpi["quota_censored"] + kpi["cancelled"]
        ):
            raise ValueError("mission count does not conserve")
        counts[(record["split"], record["profile"])] += 1
        for key in ("all", record["profile"], record["split"]):
            total = totals.setdefault(key, Counter())
            total.update(
                {
                    name: kpi[name]
                    for name in (
                        "missions",
                        "quota_reached",
                        "quota_censored",
                        "cancelled",
                        "on_time_reached",
                        "known_late",
                        "timing_unknown",
                    )
                }
            )
            total["rolling_samples"] += record["rows"]["rolling_observations.jsonl"]
    if any(
        counts[(split, profile)] != count
        for split, count in SPLIT_COUNTS.items()
        for profile in PROFILES
    ):
        raise ValueError("per-profile split counts mismatch")
    return {
        "batch_version": 1,
        "passed": True,
        "plan_sha256": plan["plan_sha256"],
        "verified_runs": 90,
        "paired_groups": 30,
        "split_run_counts": {split: count * 3 for split, count in SPLIT_COUNTS.items()},
        "distributions": {key: dict(value) for key, value in totals.items()},
        "test_used_for_tuning": False,
        "limitations": [
            "Synthetic data; no predictive quality evaluated",
            "Snapshots are dependent within missions and paired seed groups",
            "Completion-only duration means do not represent censored missions",
        ],
    }


def run_batch(directory, workers=6):
    if type(workers) is not int or not 1 <= workers <= 8:
        raise ValueError("workers must be an integer in 1..8")
    root = Path(directory).resolve()
    if not root.exists():
        root.mkdir(parents=True)
        for name in ("records", "bundles", "traces"):
            (root / name).mkdir()
        plan = make_plan()
        write_json(root / "plan.json", plan)
    else:
        plan = json.loads((root / "plan.json").read_text())
        validate_plan(plan)
    if source_hashes() != plan["source_sha256"]:
        raise ValueError("cannot resume with changed simulator sources")
    payloads, accepted = [], []
    for row in plan["runs"]:
        previous = [
            json.loads(p.read_text())
            for p in sorted(
                (root / "records").glob(f"{row['simulation_id']}-attempt-*.json")
            )
        ]
        valid = [r for r in previous if r.get("valid") is True]
        if len(valid) > 1:
            raise ValueError("multiple valid attempts; explicit review required")
        if valid:
            accepted.append(valid[0])
        else:
            attempt = max((r["attempt"] for r in previous), default=0) + 1
            payloads.append((str(root), row, plan, attempt))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(execute_run, payload) for payload in payloads]
        for future in as_completed(futures):
            record = future.result()
            if record["valid"]:
                accepted.append(record)
            write_json(
                root / "progress.json",
                {
                    "verified_runs": len(accepted),
                    "expected_runs": 90,
                    "latest": {
                        k: record[k] for k in ("simulation_id", "valid", "wall_seconds")
                    },
                },
            )
            print(
                json.dumps(
                    {
                        "completed_valid": len(accepted),
                        "run": record["simulation_id"],
                        "valid": record["valid"],
                        "wall_seconds": record["wall_seconds"],
                        "error": record.get("error"),
                    }
                ),
                flush=True,
            )
        if len(accepted) != 90:
            write_json(
                root / "acceptance.json",
                {
                    "passed": False,
                    "valid_runs": len(accepted),
                    "reason": "missing valid runs; failed attempts preserved",
                },
            )
            return False
        rows = {(r["seed"], r["profile"]): r for r in plan["runs"]}
        audits = [
            pool.submit(
                audit_record, (str(root), rows[(r["seed"], r["profile"])], plan, r)
            )
            for r in accepted
        ]
        verified = []
        for future in as_completed(audits):
            verified.append(future.result())
            print(
                json.dumps({"final_audited": len(verified), "expected": 90}), flush=True
            )
    report = summarize(plan, verified)
    write_json(root / "acceptance.json", report)
    write_json(
        root / "split_manifest.json",
        {
            "plan_sha256": plan["plan_sha256"],
            "sets": {
                split: [
                    r
                    for r in sorted(verified, key=lambda r: r["simulation_id"])
                    if r["split"] == split
                ]
                for split in SPLIT_COUNTS
            },
        },
    )
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Produce and verify the frozen D03 90-run dataset"
    )
    parser.add_argument("directory")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    raise SystemExit(0 if run_batch(args.directory, args.workers) else 1)
