"""Fit rolling M02 and diagnose intervals using training groups only."""

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from logistics import initial_prediction as ip  # noqa: E402
from logistics import rolling_prediction as rp  # noqa: E402


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def compressed_records(path, records):
    with path.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
        for record in records:
            gz.write((json.dumps(record, allow_nan=False) + "\n").encode())


def bootstrap(rows, predictions, task):
    groups = sorted({r["group"] for r in rows})
    indices = {
        g: np.array([i for i, r in enumerate(rows) if r["group"] == g]) for g in groups
    }
    y = np.array(
        [
            r["target"]["late" if task == "classification" else "target_minutes"]
            for r in rows
        ]
    )
    w = rp.weights(rows)
    rng = np.random.default_rng(1402)
    values = []
    for _ in range(400):
        idx = np.concatenate(
            [indices[g] for g in rng.choice(groups, len(groups), replace=True)]
        )
        error = (
            (y[idx] - predictions[idx]) ** 2
            if task == "classification"
            else abs(y[idx] - predictions[idx])
        )
        values.append(float(np.average(error, weights=w[idx])))
    return [float(v) for v in np.quantile(values, [0.025, 0.975])]


def availability(rows, predictions):
    results = {}
    for regime in ("pre", "post"):
        idx = [i for i, r in enumerate(rows) if r["x"]["regime"] == regime]
        members = [rows[i] for i in idx]
        w = rp.weights(members)
        results[regime] = {
            "snapshots": len(idx),
            "missions": len({tuple(r["key"]) for r in members}),
            "statuses": dict(Counter(predictions[i]["status"] for i in idx)),
            "weighted_duration_availability": float(
                np.average(
                    [
                        predictions[i]["duration_interval_minutes"] is not None
                        for i in idx
                    ],
                    weights=w,
                )
            ),
            "weighted_probability_availability": float(
                np.average(
                    [predictions[i]["probability_late"] is not None for i in idx],
                    weights=w,
                )
            ),
            "censored_missions": len(
                {tuple(r["key"]) for r in members if r["target"]["quota_censored"]}
            ),
        }
    return results


def initial_interval_metrics(model, creations):
    covered, widths = [], []
    eligible = 0
    for r in creations:
        if not r["masks"]["delay_regression"]:
            continue
        eligible += 1
        p = model.predict_creation(r["observation"])
        if p["interval"] is not None:
            lo, hi = p["interval"]
            covered.append(lo <= r["label"]["delay_minutes"] <= hi)
            widths.append(hi - lo)
    return {
        "eligible_completed_late": eligible,
        "predicted_missions": len(covered),
        "coverage": float(np.mean(covered)) if covered else None,
        "width_minutes": float(np.mean(widths)) if widths else None,
    }


def internal_interval_diagnostics(training, creations):
    groups = sorted(
        {r["group"] for r in training},
        key=lambda g: hashlib.sha256(("m02-interval-v1|" + g).encode()).digest(),
    )
    blocks = [set(groups[i : i + 6]) for i in range(0, 18, 6)]
    results = []
    for i in range(3):
        fit, cal, assess = blocks[i], blocks[(i + 1) % 3], blocks[(i + 2) % 3]
        tr = [r for r in training if r["group"] in fit]
        ca = [dict(r, split="calibration") for r in training if r["group"] in cal]
        te = [r for r in training if r["group"] in assess]
        ctr = [r for r in creations if r["group"] in fit]
        cca = [dict(r, split="calibration") for r in creations if r["group"] in cal]
        cte = [r for r in creations if r["group"] in assess]
        initial = ip.fit_final(ctr, cca, "boosting", "boosting")
        model = rp.fit_predictor(
            tr, ca, {t: "boosting" for t in ("classification", "pre", "post")}, initial
        )
        rp.calibrate_intervals(model, ca, cca)
        predictions = model.predict_many(te)
        result = {
            "fit_groups": sorted(fit),
            "calibration_groups": sorted(cal),
            "assessment_groups": sorted(assess),
            "radii": {k: asdict(v) for k, v in model.intervals.items()},
            "initial": initial_interval_metrics(model, cte),
            "rolling": {
                t: rp.interval_metrics(te, predictions, t) for t in ("pre", "post")
            },
            "availability": availability(te, predictions),
        }
        results.append(result)
        print(
            json.dumps(
                {"internal_interval_cycle": i + 1, "rolling": result["rolling"]}
            ),
            flush=True,
        )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--initial", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[1]
    protocol_sha = hashlib.sha256(
        (repo / "docs/protocollo-m02-v1.md").read_bytes()
    ).hexdigest()
    start = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": protocol_sha,
        "implementation_sha256": {
            str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                repo / "src/logistics/rolling_prediction.py",
                repo / "src/logistics/forecast_session.py",
                Path(__file__),
                repo / "scripts/prepare_m02_data.py",
            ]
        },
        "test_tables_read": 0,
        "promoted": False,
    }
    write_json(args.output / "run-start.json", start)
    metadata = json.loads((args.prepared / "manifest.json").read_text())
    sample = args.prepared / "sampled.jsonl.gz"
    if metadata["protocol_sha256"] != protocol_sha or metadata["test_tables_read"] != 0:
        raise ValueError("unapproved prepared data")
    with sample.open("rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != metadata["sha256"]:
            raise ValueError("prepared checksum mismatch")
    with gzip.open(sample, "rt") as source:
        rows = [json.loads(line) for line in source]
    if Counter(r["split"] for r in rows) != Counter(metadata["rows"]):
        raise ValueError("prepared count mismatch")
    if {r["split"] for r in rows} != {"training", "calibration"} or len(
        metadata["provenance"]
    ) != 72:
        raise ValueError("invalid prepared splits")
    if sum(r["native_snapshots"] for r in metadata["provenance"]) != 829954:
        raise ValueError("incomplete D03 development snapshots")
    for row in rows:
        if row["x"] != rp.rolling_features(row["creation"], row["observation"]):
            raise ValueError("prepared features not reproducible")
    training = [r for r in rows if r["split"] == "training"]
    calibration = [r for r in rows if r["split"] == "calibration"]
    creations, _ = ip.load_creation(args.dataset)
    ct = [r for r in creations if r["split"] == "training"]
    cc = [r for r in creations if r["split"] == "calibration"]
    initial_report = json.loads((args.initial.parent / "report.json").read_text())
    if (
        hashlib.sha256(args.initial.read_bytes()).hexdigest()
        != initial_report["artifacts"][args.initial.name]
    ):
        raise ValueError("initial model checksum mismatch")
    initial = joblib.load(args.initial)
    print(
        json.dumps(
            {
                "training_snapshots": len(training),
                "calibration_snapshots": len(calibration),
            }
        ),
        flush=True,
    )
    scores, predictions = rp.oof(training)
    choices = {
        task: min(
            values,
            key=lambda n: (
                values[n]["brier" if task == "classification" else "mae_minutes"],
                n,
            ),
        )
        for task, values in scores.items()
    }
    segments = {}
    oof_records = []
    for task, values in scores.items():
        idx = [i for i, r in enumerate(training) if rp.included(r, task)]
        selected = [training[i] for i in idx]
        p = predictions[task][choices[task]][idx]
        scores[task][choices[task]]["group_bootstrap_95"] = bootstrap(selected, p, task)
        for key in ("profile", "phase", "initial_urgent", "initial_cold"):
            vals = sorted(
                {r["profile"] if key == "profile" else r["x"][key] for r in selected}
            )
            for value in vals:
                sub = [
                    j
                    for j, r in enumerate(selected)
                    if (r["profile"] if key == "profile" else r["x"][key]) == value
                ]
                result = rp.metrics([selected[j] for j in sub], p[sub], task)
                result["small_segment"] = (
                    result["missions"] < 30 or result["groups"] < 3
                )
                segments[f"{task}|{key}={value}"] = result
        w = rp.weights(selected)
        for j, i in enumerate(idx):
            r = training[i]
            oof_records.append(
                {
                    "key": r["key"],
                    "observation_id": r["observation"]["observation_id"],
                    "observed_s": r["observation"]["observed_s"],
                    "group": r["group"],
                    "task": task,
                    "mission_weight": float(w[j]),
                    "target": r["target"],
                    "predictions": {
                        n: float(v[i]) for n, v in predictions[task].items()
                    },
                }
            )
    compressed_records(args.output / "training-oof.jsonl.gz", oof_records)
    print(json.dumps({"selected": choices, "scores": scores}), flush=True)
    diagnostic = internal_interval_diagnostics(training, ct)
    model = rp.fit_predictor(training, calibration, choices, initial)
    rp.calibrate_intervals(model, calibration, cc)
    artifact = args.output / "rolling_predictor.joblib"
    joblib.dump(model, artifact, compress=3)
    model_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    outputs = model.predict_many(calibration)
    compressed_records(
        args.output / "calibration-inference.jsonl.gz",
        (
            {
                "snapshot": r["observation"],
                "creation_snapshot": r["creation"],
                "model_sha256": model_sha,
                **p,
            }
            for r, p in zip(calibration, outputs)
        ),
    )
    examples = {}
    for regime in ("pre", "post"):
        i = next(
            i
            for i, (r, p) in enumerate(zip(calibration, outputs))
            if r["x"]["regime"] == regime and p["duration_interval_minutes"] is not None
        )
        r = calibration[i]
        examples[regime] = {"creation": r["creation"], "observation": r["observation"]}
    write_json(args.output / "example_inputs.json", examples)
    report = {
        **start,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "selection": "training_only_group_oof_uncalibrated",
        "selected": choices,
        "scores": scores,
        "segments": segments,
        "data": metadata,
        "internal_interval_diagnostics": diagnostic,
        "intervals": {k: asdict(v) for k, v in model.intervals.items()},
        "calibration_inference_availability": availability(calibration, outputs),
        "calibration_fit_interval_metrics_not_independent": {
            t: rp.interval_metrics(calibration, outputs, t) for t in ("pre", "post")
        },
        "calibration_fit_initial_interval_metrics": initial_interval_metrics(model, cc),
        "initial_source_sha256": hashlib.sha256(args.initial.read_bytes()).hexdigest(),
        "versions": initial_report["versions"],
        "artifacts": {},
    }
    for name in (
        "rolling_predictor.joblib",
        "training-oof.jsonl.gz",
        "calibration-inference.jsonl.gz",
        "example_inputs.json",
    ):
        report["artifacts"][name] = hashlib.sha256(
            (args.output / name).read_bytes()
        ).hexdigest()
    write_json(args.output / "report.json", report)
    print(
        json.dumps(
            {
                "intervals": report["intervals"],
                "availability": report["calibration_inference_availability"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
