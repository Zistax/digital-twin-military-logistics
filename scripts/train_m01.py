"""Reproduce M01 without opening final-test tables or fitting on their labels."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys

import joblib
import numpy as np
import sklearn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from logistics.initial_prediction import (  # noqa: E402
    CLASSIFIERS,
    REGRESSORS,
    PLAN_SHA,
    classification_metrics,
    delay_metrics,
    fit_final,
    load_creation,
    oof_predictions,
    operational_delay,
)


def bootstrap(rows, y, p, regression=False):
    groups = sorted({r["group"] for r in rows})
    indices = {
        g: np.array([i for i, r in enumerate(rows) if r["group"] == g]) for g in groups
    }
    rng = np.random.default_rng(1401)
    values = []
    for _ in range(400):
        idx = np.concatenate(
            [indices[g] for g in rng.choice(groups, len(groups), replace=True)]
        )
        metric = (
            float(np.mean(abs(y[idx] - p[idx])))
            if regression
            else float(np.mean((y[idx] - p[idx]) ** 2))
        )
        values.append(metric)
    return [float(v) for v in np.quantile(values, [0.025, 0.975])]


def summarise(rows, probabilities, delays):
    cls_idx = [i for i, r in enumerate(rows) if r["masks"]["classification"]]
    reg_idx = [i for i, r in enumerate(rows) if r["masks"]["delay_regression"]]
    y = np.array([rows[i]["label"]["late"] for i in cls_idx])
    dy = np.array([rows[i]["label"]["delay_minutes"] for i in reg_idx])
    cr = [rows[i] for i in cls_idx]
    rr = [rows[i] for i in reg_idx]
    results = {"classification": {}, "conditional_delay": {}}
    for name, p in probabilities.items():
        score = classification_metrics(y, p[cls_idx])
        score["brier_group_bootstrap_95"] = bootstrap(cr, y, p[cls_idx])
        results["classification"][name] = score
    baseline = [operational_delay(r["x"]) for r in rr]
    shared = [i for i, p in enumerate(baseline) if p is not None]
    results["conditional_delay"]["operational"] = delay_metrics(dy, baseline)
    for name, p in delays.items():
        score = delay_metrics(dy, p[reg_idx])
        score["mae_group_bootstrap_95"] = bootstrap(rr, dy, p[reg_idx], True)
        score["operational_common_subset"] = delay_metrics(
            dy[shared], p[reg_idx][shared]
        )
        results["conditional_delay"][name] = score
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[1]
    protocol = repo / "docs/protocollo-m01-v1.md"
    protocol_sha = hashlib.sha256(protocol.read_bytes()).hexdigest()
    # Persist protocol identity before the first label is loaded or model fitted.
    started = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": protocol_sha,
        "plan_sha256": PLAN_SHA,
        "test_tables_allowed": False,
        "implementation_sha256": {
            str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (repo / "src/logistics/initial_prediction.py", Path(__file__))
        },
    }
    (args.output / "run-start.json").write_text(json.dumps(started, indent=2))
    rows, provenance = load_creation(args.dataset)
    training = [r for r in rows if r["split"] == "training"]
    calibration = [r for r in rows if r["split"] == "calibration"]
    if (len(training), len(calibration)) != (4949, 1646):
        raise ValueError("unexpected frozen D03 mission counts")
    probabilities, delays, fold = oof_predictions(training)
    scores = summarise(training, probabilities, delays)
    classifier = min(
        CLASSIFIERS, key=lambda n: (scores["classification"][n]["brier"], n)
    )
    regressor = min(
        REGRESSORS, key=lambda n: (scores["conditional_delay"][n]["mae_minutes"], n)
    )
    predictor = fit_final(training, calibration, classifier, regressor)
    joblib.dump(predictor, args.output / "initial_predictor.joblib", compress=3)
    inference = [
        dict(
            simulation_id=r["key"][0],
            mission_id=r["key"][1],
            **predictor.predict(r["observation"]),
        )
        for r in calibration
    ]
    (args.output / "calibration-inference.jsonl").write_text(
        "".join(json.dumps(r, allow_nan=False) + "\n" for r in inference)
    )
    selected_p, selected_d = probabilities[classifier], delays[regressor]
    segments = {}
    for key in ("profile", "urgent", "cold"):
        values = sorted({r[key] if key == "profile" else r["x"][key] for r in training})
        for value in values:
            idx = [
                i
                for i, r in enumerate(training)
                if (r[key] if key == "profile" else r["x"][key]) == value
            ]
            group = [training[i] for i in idx]
            count = len({r["group"] for r in group})
            segments[f"{key}={value}"] = {
                "groups": count,
                "n": len(idx),
                "small_segment": len(idx) < 30 or count < 3,
                "censored": sum(r["masks"]["censored"] for r in group),
                **summarise(
                    group, {classifier: selected_p[idx]}, {regressor: selected_d[idx]}
                ),
            }
    records = []
    for i, r in enumerate(training):
        records.append(
            {
                "simulation_id": r["key"][0],
                "mission_id": r["key"][1],
                "group": r["group"],
                "fold": int(fold[i]),
                "late": r["label"]["late"],
                "delay_minutes": r["label"]["delay_minutes"],
                "quota_censored": r["masks"]["censored"],
                "probabilities": {n: float(p[i]) for n, p in probabilities.items()},
                "conditional_delays": {n: float(p[i]) for n, p in delays.items()},
            }
        )
    (args.output / "training-oof.jsonl").write_text(
        "".join(json.dumps(r, allow_nan=False) + "\n" for r in records)
    )
    report = {
        **started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "selection_data": "training_group_out_of_fold_uncalibrated",
        "selected_classifier": classifier,
        "selected_conditional_delay": regressor,
        "scores": scores,
        "segments": segments,
        "training_missions": len(training),
        "calibration_missions": len(calibration),
        "calibration_inference_status_counts": {
            status: sum(r["status"] == status for r in inference)
            for status in sorted({r["status"] for r in inference})
        },
        "test_tables_read": 0,
        "training_censored": sum(r["masks"]["censored"] for r in training),
        "regression_completed_late": sum(
            r["masks"]["delay_regression"] for r in training
        ),
        "sigmoid_fit": {
            "data": "calibration_only",
            "coefficient": float(predictor.calibrator.coef_[0, 0]),
            "intercept": float(predictor.calibrator.intercept_[0]),
            "independent_performance_estimate": False,
        },
        "support": predictor.support,
        "provenance": provenance,
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "sklearn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
        "artifacts": {},
        "promoted": False,
        "intervals": "M02 pending",
        "limitations": [
            "synthetic data",
            "duration conditional on completed late missions",
            "censoring is not ignorable",
            "no final-test performance claim",
        ],
    }
    for filename in (
        "initial_predictor.joblib",
        "training-oof.jsonl",
        "calibration-inference.jsonl",
    ):
        report["artifacts"][filename] = hashlib.sha256(
            (args.output / filename).read_bytes()
        ).hexdigest()
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "selected_classifier",
                    "selected_conditional_delay",
                    "scores",
                    "test_tables_read",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
