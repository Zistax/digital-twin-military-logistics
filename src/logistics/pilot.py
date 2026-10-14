"""Small paired-seed pilot. Checkpoints each run and verifies exported data."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

from .bundles import read_verified_bundle
from .dataset import build_creation_dataset, export_creation_dataset
from .experiments import run_experiment
from .scenarios import ScenarioConfig
from .core import natural


def run_pilot(directory, seeds=(0,), generation_days=7, extension_days=7):
    seeds = tuple(seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("nonempty unique pilot seeds required")
    for seed in seeds:
        natural(seed, "seed")
        ScenarioConfig(seed, "regular", generation_days, extension_days)
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    records = []
    for seed in seeds:
        for profile in ("regular", "pressure", "perturbed"):
            config = ScenarioConfig(seed, profile, generation_days, extension_days)
            start = perf_counter()
            record = {"seed": seed, "profile": profile}
            try:
                result = run_experiment(config, capture_trace=True)
                bundle = root / f"seed-{seed}-{profile}"
                export_creation_dataset(result, bundle)
                read_verified_bundle(bundle)
                data = build_creation_dataset(result)
                trace = "".join(
                    json.dumps(row, sort_keys=True, allow_nan=False) + "\n"
                    for row in result["operational_trace"]
                )
                trace_path = root / f"trace-{seed}-{profile}.jsonl"
                trace_path.write_bytes(trace.encode())
                canonical = json.dumps(
                    result, sort_keys=True, default=str, allow_nan=False
                ).encode()
                record.update(
                    {
                        "valid": True,
                        "kpi": data["kpi"],
                        "stopped_s": result["stopped_s"],
                        "stop_reason": result["stop_reason"],
                        "rolling_samples": len(result["rolling_observations"]),
                        "deadline_sources": dict(
                            Counter(c["deadline_source"] for c in result["creations"])
                        ),
                        "estimate_unavailable_reasons": dict(
                            Counter(
                                c["estimate"]["reason"]
                                for c in result["creations"]
                                if c["estimate"]["duration_s"] is None
                            )
                        ),
                        "diagnostics": result["diagnostics"],
                        "result_sha256": sha256(canonical).hexdigest(),
                        "trace_rows": len(result["operational_trace"]),
                        "trace_sha256": sha256(trace.encode()).hexdigest(),
                        "unexplained_open_missions": [
                            mid
                            for mid, reasons in result["diagnostics"][
                                "terminal_blockers"
                            ].items()
                            if not reasons
                        ],
                    }
                )
            except Exception as error:
                record.update(
                    {
                        "valid": False,
                        "error_type": type(error).__name__,
                        "error": str(error),
                    }
                )
            record["wall_seconds"] = round(perf_counter() - start, 3)
            records.append(record)
            (root / f"seed-{seed}-{profile}.json").write_text(
                json.dumps(record, indent=2, sort_keys=True), encoding="utf-8"
            )
            print(
                json.dumps(
                    {k: record[k] for k in ("seed", "profile", "valid", "wall_seconds")}
                ),
                flush=True,
            )
    report = {
        "pilot_version": 1,
        "generation_days": generation_days,
        "extension_days": extension_days,
        "seeds": list(seeds),
        "runs": records,
        "all_valid": all(r["valid"] for r in records),
        "limitations": [
            "Exploratory pilot, not the 90-run dataset or statistical validation",
            "Predictive quality and the independent 90-run dataset are not evaluated",
            "Queue peaks sampled at observation intervals, not continuous maxima",
        ],
    }
    (root / "pilot.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Paired pilot across three logistics profiles"
    )
    parser.add_argument("directory")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0])
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--extension-days", type=int, default=7)
    args = parser.parse_args()
    run_pilot(args.directory, tuple(args.seeds), args.days, args.extension_days)
