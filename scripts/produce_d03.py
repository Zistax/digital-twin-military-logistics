"""Memory-bounded execution of the frozen D03 engine and plan.

Release the simulated state before parsing its persisted bundle. The physics,
seed assignment, source files and table contracts remain the frozen versions.
"""

from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import gc
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
import traceback

from src.logistics.batch import (
    audit_record,
    source_hashes,
    summarize,
    table_counts,
    validate_plan,
    verify_bundle,
    write_json,
)
from src.logistics.bundles import read_verified_bundle
from src.logistics.dataset import build_creation_dataset, export_creation_dataset
from src.logistics.experiments import run_experiment
from src.logistics.scenarios import ScenarioConfig


def execute_released(payload):
    root_text, row, plan, attempt = payload
    root = Path(root_text)
    start = perf_counter()
    name = row["simulation_id"]
    record = {**row, "attempt": attempt, "plan_sha256": plan["plan_sha256"]}
    try:
        if source_hashes() != plan["source_sha256"]:
            raise ValueError("source changed after freeze")
        result = run_experiment(
            ScenarioConfig(row["seed"], row["profile"], 7, 7), capture_trace=True
        )
        path = root / "bundles" / f"{name}-attempt-{attempt}"
        export_creation_dataset(result, path)
        kpi = build_creation_dataset(result)["kpi"]
        trace_path = root / "traces" / f"{name}-attempt-{attempt}.jsonl"
        trace = "".join(
            json.dumps(value, sort_keys=True, allow_nan=False) + "\n"
            for value in result["operational_trace"]
        )
        trace_path.write_text(trace)
        unexplained = [
            mid
            for mid, reasons in result["diagnostics"]["terminal_blockers"].items()
            if not reasons
        ]
        if unexplained or not result["operational_trace"]:
            raise ValueError("missing trace or unexplained open mission")
        record.update(
            {
                "bundle": str(path.relative_to(root)),
                "kpi": kpi,
                "trace": str(trace_path.relative_to(root)),
                "trace_sha256": sha256(trace.encode()).hexdigest(),
                "stopped_s": result["stopped_s"],
                "stop_reason": result["stop_reason"],
                "unexplained_open_missions": unexplained,
            }
        )
        # No simulated object is needed for the independent persistence gate.
        del result, trace
        gc.collect()
        bundle = read_verified_bundle(path)
        verify_bundle(bundle, row, plan)
        record.update(table_counts(bundle))
        if source_hashes() != plan["source_sha256"]:
            raise ValueError("source changed during run")
        record.update(
            {
                "valid": True,
                "manifest_sha256": sha256(
                    (path / "manifest.json").read_bytes()
                ).hexdigest(),
                "executor": "release-before-independent-read-v1",
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
    record["wall_seconds"] = round(perf_counter() - start, 3)
    write_json(root / "records" / f"{name}-attempt-{attempt}.json", record)
    return record


def bounded_map(pool, function, payloads, workers, heavy_limit):
    pending = list(payloads)
    running = {}
    while pending or running:
        heavy = sum(payload[1]["profile"] == "pressure" for payload in running.values())
        while pending and len(running) < workers:
            index = next(
                (
                    i
                    for i, p in enumerate(pending)
                    if p[1]["profile"] != "pressure" or heavy < heavy_limit
                ),
                None,
            )
            if index is None:
                break
            payload = pending.pop(index)
            running[pool.submit(function, payload)] = payload
            heavy += payload[1]["profile"] == "pressure"
        done, _ = wait(running, return_when=FIRST_COMPLETED)
        for future in done:
            running.pop(future)
            yield future.result()


def continue_batch(root, workers=5, heavy_limit=2):
    if not 1 <= heavy_limit <= workers <= 5:
        raise ValueError("require 1 <= heavy_limit <= workers <= 5")
    root = root.resolve()
    plan = json.loads((root / "plan.json").read_text())
    validate_plan(plan)
    if source_hashes() != plan["source_sha256"]:
        raise ValueError("cannot resume with changed engine")
    accepted, payloads = [], []
    for row in plan["runs"]:
        previous = [
            json.loads(p.read_text())
            for p in (root / "records").glob(f"{row['simulation_id']}-attempt-*.json")
        ]
        valid = [r for r in previous if r.get("valid") is True]
        if len(valid) > 1:
            raise ValueError("multiple valid attempts")
        if valid:
            accepted.append(valid[0])
        else:
            attempt = max((r["attempt"] for r in previous), default=0) + 1
            payloads.append((str(root), row, plan, attempt))
    executor_file = Path(__file__)
    policy_file = root / "memory-executor.json"
    policy = {
        "executor_sha256": sha256(executor_file.read_bytes()).hexdigest(),
        "workers": workers,
        "pressure_limit": heavy_limit,
        "plan_sha256": plan["plan_sha256"],
        "release_state_before_read": True,
    }
    if policy_file.exists():
        if json.loads(policy_file.read_text()) != policy:
            raise ValueError(
                "memory executor changed; explicit new execution record required"
            )
    else:
        write_json(policy_file, policy)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for record in bounded_map(
            pool, execute_released, payloads, workers, heavy_limit
        ):
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
                root / "acceptance.json", {"passed": False, "valid_runs": len(accepted)}
            )
            return False
        indexed = {(r["seed"], r["profile"]): r for r in plan["runs"]}
        audits = [
            (str(root), indexed[(r["seed"], r["profile"])], plan, r) for r in accepted
        ]
        verified = []
        for record in bounded_map(pool, audit_record, audits, workers, heavy_limit):
            verified.append(record)
            print(
                json.dumps({"final_audited": len(verified), "expected": 90}), flush=True
            )
    write_json(root / "acceptance.json", summarize(plan, verified))
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
                for split in ("training", "calibration", "test")
            },
        },
    )
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--pressure-limit", type=int, default=2)
    args = parser.parse_args()
    raise SystemExit(
        0 if continue_batch(args.directory, args.workers, args.pressure_limit) else 1
    )
