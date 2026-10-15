"""Freeze train-only baselines, then evaluate immutable candidates once on D03 test."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import joblib
import numpy as np

from prepare_m01_data import ARCHIVE_SHA256
from prepare_m02_data import sample_observations
from train_m02 import compressed_records

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from logistics import initial_prediction as ip  # noqa: E402
from logistics import rolling_prediction as rp  # noqa: E402
from logistics import final_evaluation as ev  # noqa: E402
from logistics import model_registry as registry  # noqa: E402


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def files_to_freeze(repo):
    return [
        repo / p
        for p in [
            "docs/protocollo-m03-v1.md",
            "src/logistics/final_evaluation.py",
            "src/logistics/model_registry.py",
            "scripts/evaluate_m03.py",
            "scripts/prepare_m02_data.py",
            "scripts/prepare_m01_data.py",
            "scripts/train_m02.py",
            "reports/m01-v1/report.json",
            "reports/m02-v1/report.json",
            "reports/quality-m03-final-20261015/quality.json",
            "src/logistics/initial_prediction.py",
            "src/logistics/rolling_prediction.py",
            "src/logistics/forecast_session.py",
        ]
    ]


def freeze(repo, out):
    out = Path(out).resolve()
    if (out / "freeze.json").exists():
        raise ValueError("protocol already frozen; do not refit baselines")
    creations, _ = ip.load_creation(repo / "reports/d03-batch-v1")
    training = [r for r in creations if r["split"] == "training"]
    data = repo / "reports/m02-v1/data/sampled.jsonl.gz"
    metadata = json.loads((data.parent / "manifest.json").read_text())
    if registry.sha256(data) != metadata["sha256"]:
        raise ValueError("development sample checksum mismatch")
    with gzip.open(data, "rt") as source:
        rolling = [
            json.loads(line)
            for line in source
            if json.loads(line)["split"] == "training"
        ]
    baselines = {"initial": {}, "rolling": {}}
    for name in ("prevalence", "operational"):
        rows = [r for r in training if r["masks"]["classification"]]
        model = ip.estimator(name)
        model.fit(ip.inputs(rows, name), [r["label"]["late"] for r in rows])
        baselines["initial"][name] = model
    rows = [r for r in training if r["masks"]["delay_regression"]]
    model = ip.estimator("median", regression=True)
    model.fit(ip.inputs(rows, "median"), [r["label"]["delay_minutes"] for r in rows])
    baselines["initial"]["median"] = model
    for task, name in [
        ("classification", "prevalence"),
        ("pre", "median"),
        ("post", "median"),
    ]:
        baselines["rolling"][task] = rp.fit_model(rolling, name, task)
    joblib.dump(baselines, out / "baselines.joblib", compress=3)
    candidate_paths = [
        repo / "reports/m01-v1/initial_predictor.joblib",
        repo / "reports/m02-v1/rolling_predictor.joblib",
    ]
    for path in candidate_paths:
        report = json.loads((path.parent / "report.json").read_text())
        if registry.sha256(path) != report["artifacts"][path.name]:
            raise ValueError("candidate checksum mismatch")
        for relative, sha in report["implementation_sha256"].items():
            if registry.sha256(repo / relative) != sha:
                raise ValueError("candidate implementation changed")
    paths = (
        files_to_freeze(repo)
        + candidate_paths
        + [
            out / "baselines.joblib",
            repo / "reports/d03-batch-v1/plan.json",
            repo / "reports/d03-batch-v1/split_manifest.json",
            data,
        ]
    )
    record = {
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "policy": ev.POLICY,
        "sha256": {str(p.relative_to(repo)): registry.sha256(p) for p in paths},
        "training_groups": sorted({r["group"] for r in training}),
        "calibration_groups": sorted(
            {r["group"] for r in creations if r["split"] == "calibration"}
        ),
        "test_tables_opened": False,
        "versions": report.get("versions", {}),
    }
    write_json(out / "freeze.json", record)
    print(
        json.dumps(
            {
                "frozen": True,
                "test_tables_opened": False,
                "sha256": registry.sha256(out / "freeze.json"),
            }
        )
    )


def verified_table(archive, prefix, manifest, name):
    digest = hashlib.sha256()
    rows = []
    with archive.open(prefix + name) as source:
        for raw in source:
            digest.update(raw)
            rows.append(json.loads(raw))
    meta = manifest["files"][name]
    if digest.hexdigest() != meta["sha256"] or len(rows) != meta["rows"]:
        raise ValueError("table checksum/count mismatch")
    return rows


def load_test(repo, archives):
    split = json.loads((repo / "reports/d03-batch-v1/split_manifest.json").read_text())
    accepted = {r["bundle"]: r for r in split["sets"]["test"]}
    creations, rolling, provenance, seen = [], [], [], set()
    for i, expected in enumerate(ARCHIVE_SHA256, 1):
        path = archives / f"Dataset_D03_Parte_{i}_di_4.zip"
        if registry.sha256(path) != expected:
            raise ValueError("archive checksum mismatch")
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            for folder, record in accepted.items():
                prefix = "d03-batch-v1/" + folder + "/"
                if prefix + "manifest.json" not in names:
                    continue
                raw = archive.read(prefix + "manifest.json")
                if hashlib.sha256(raw).hexdigest() != record["manifest_sha256"]:
                    raise ValueError("manifest checksum mismatch")
                manifest = json.loads(raw)
                originals = verified_table(
                    archive, prefix, manifest, "observations.jsonl"
                )
                labels = verified_table(archive, prefix, manifest, "labels.jsonl")
                label_map = {r["mission_id"]: r for r in labels}
                original_map = {r["mission_id"]: r for r in originals}
                if (
                    len(label_map) != len(labels)
                    or len(original_map) != len(originals)
                    or label_map.keys() != original_map.keys()
                ):
                    raise ValueError("creation pairing mismatch")
                for obs in originals:
                    if obs["simulation_id"] != record["simulation_id"]:
                        raise ValueError("creation simulation mismatch")
                    label = label_map[obs["mission_id"]]
                    creations.append(
                        {
                            "key": [obs["simulation_id"], obs["mission_id"]],
                            "group": record["group_id"],
                            "split": "test",
                            "profile": record["profile"],
                            "observation": obs,
                            "label": label,
                            "x": ip.features(obs),
                            "masks": ip.creation_masks(label),
                        }
                    )
                with archive.open(prefix + "rolling_observations.jsonl") as source:
                    sampled, count, sha = sample_observations(source)
                meta = manifest["files"]["rolling_observations.jsonl"]
                if (count, sha) != (meta["rows"], meta["sha256"]):
                    raise ValueError("rolling checksum/count mismatch")
                # Targets are read only after the observable sample is fixed.
                targets = verified_table(
                    archive, prefix, manifest, "rolling_targets.jsonl"
                )
                targets = {
                    r["observation_id"]: r
                    for r in targets
                    if r["observation_id"] in sampled
                }
                if targets.keys() != sampled.keys():
                    raise ValueError("rolling pairing mismatch")
                for oid, obs in sorted(sampled.items()):
                    creation = original_map[obs["mission_id"]]
                    target = targets[oid]
                    if any(
                        target[k] != obs[k]
                        for k in ("simulation_id", "mission_id", "observation_id")
                    ):
                        raise ValueError("rolling identity mismatch")
                    x = rp.rolling_features(creation, obs)
                    kind = (
                        "delay_if_late"
                        if x["regime"] == "pre"
                        else "remaining_after_deadline"
                    )
                    if (
                        target["target_kind"] != kind
                        or target["label_cutoff_s"] < obs["observed_s"]
                    ):
                        raise ValueError("rolling target contract mismatch")
                    rolling.append(
                        {
                            "key": [obs["simulation_id"], obs["mission_id"]],
                            "group": record["group_id"],
                            "split": "test",
                            "profile": record["profile"],
                            "creation": creation,
                            "observation": obs,
                            "x": x,
                            "target": target,
                        }
                    )
                provenance.append(
                    {
                        "simulation_id": record["simulation_id"],
                        "group": record["group_id"],
                        "manifest_sha256": record["manifest_sha256"],
                        "native_rolling": count,
                        "sampled_rolling": len(sampled),
                        "files": manifest["files"],
                    }
                )
                seen.add(folder)
                print(
                    json.dumps(
                        {
                            "test_run_verified": record["simulation_id"],
                            "runs": len(seen),
                        }
                    ),
                    flush=True,
                )
    if (
        seen != set(accepted)
        or len(seen) != 18
        or len({r["group"] for r in creations}) != 6
    ):
        raise ValueError("incomplete final test")
    if len(creations) != 1644 or sum(p["native_rolling"] for p in provenance) != 210287:
        raise ValueError("unexpected frozen test counts")
    return creations, rolling, provenance


def evaluation_record(row, duration=None, creation=False):
    x = row["x"]
    return {
        "key": row["key"],
        "group": row["group"],
        "profile": row["profile"],
        "urgent": x["urgent" if creation else "initial_urgent"],
        "cold": x["cold" if creation else "initial_cold"],
        "phase": "creation" if creation else x["phase"],
        "late": row["label" if creation else "target"]["late"],
        "duration": duration,
    }


def score_channel(rows, point, baseline, classification, intervals=None):
    m = ev.summary(
        rows,
        probability=point if classification else None,
        duration=None if classification else point,
        intervals=intervals,
        baseline=baseline,
    )
    if rows:
        m.update(ev.uncertainty(rows, point, baseline, classification, intervals))
    return m


def evaluate(repo, out, archives):
    out = Path(out).resolve()
    frozen = json.loads((out / "freeze.json").read_text())
    if frozen["policy"] != ev.POLICY:
        raise ValueError("eligibility policy changed")
    for relative, sha in frozen["sha256"].items():
        if registry.sha256(repo / relative) != sha:
            raise ValueError("frozen input changed: " + relative)
    quality = json.loads(
        (repo / "reports/quality-m03-final-20261015/quality.json").read_text()
    )
    if not quality["passed"]:
        raise ValueError("quality gate must pass before test access")
    if (out / "attempt.json").exists():
        raise ValueError("test already attempted; inspect evidence before any resume")
    with (out / "attempt.json").open("x") as attempt:
        json.dump(
            {
                "opened_utc": datetime.now(timezone.utc).isoformat(),
                "freeze_sha256": registry.sha256(out / "freeze.json"),
            },
            attempt,
        )
    creations, rolling, provenance = load_test(repo, archives)
    groups = {r["group"] for r in creations}
    if groups & set(frozen["training_groups"] + frozen["calibration_groups"]):
        raise ValueError("test group leakage")
    baseline = joblib.load(out / "baselines.joblib")
    initial = joblib.load(repo / "reports/m01-v1/initial_predictor.joblib")
    model = joblib.load(repo / "reports/m02-v1/rolling_predictor.joblib")
    cp = [model.predict_creation(r["observation"]) for r in creations]
    rp_outputs = model.predict_many(rolling)
    channels, segments, raw_metrics = {}, {}, {}
    available = {}
    available["initial"] = {
        "probability": float(np.mean([p["probability_late"] is not None for p in cp])),
        "duration": float(np.mean([p["interval"] is not None for p in cp])),
    }
    selections = {}
    for classification in (True, False):
        idx = [
            i
            for i, r in enumerate(creations)
            if r["masks"]["classification" if classification else "delay_regression"]
            and (
                cp[i]["probability_late"] is not None
                if classification
                else cp[i]["interval"] is not None
            )
        ]
        rows = [
            evaluation_record(
                creations[i], creations[i]["label"]["delay_minutes"], True
            )
            for i in idx
        ]
        point = np.array(
            [
                cp[i][
                    (
                        "probability_late"
                        if classification
                        else "conditional_delay_minutes"
                    )
                ]
                for i in idx
            ]
        )
        inputs = [creations[i] for i in idx]
        b = (
            []
            if not inputs
            else (
                baseline["initial"]["prevalence"].predict_proba(
                    ip.inputs(inputs, "prevalence")
                )[:, 1]
                if classification
                else baseline["initial"]["median"].predict(ip.inputs(inputs, "median"))
            )
        )
        intervals = None if classification else [cp[i]["interval"] for i in idx]
        name = "initial_classification" if classification else "initial_duration"
        channels[name] = score_channel(rows, point, b, classification, intervals)
        selections[name] = (rows, point, np.array(b), intervals)
    # Raw models are evaluated on the complete eligible cohort as diagnostics.
    for classification in (True, False):
        members = [
            r
            for r in creations
            if r["masks"]["classification" if classification else "delay_regression"]
        ]
        rows = [
            evaluation_record(r, r["label"]["delay_minutes"], True) for r in members
        ]
        if classification:
            point = initial.classifier.predict_proba(
                ip.inputs(members, initial.classifier_name)
            )[:, 1]
            logits = np.log(
                np.clip(point, 1e-6, 1 - 1e-6) / np.clip(1 - point, 1e-6, 1)
            )
            point = initial.calibrator.predict_proba(logits.reshape(-1, 1))[:, 1]
            b = baseline["initial"]["prevalence"].predict_proba(
                ip.inputs(members, "prevalence")
            )[:, 1]
        else:
            point = initial.regressor.predict(
                ip.inputs(members, initial.regressor_name)
            )
            b = baseline["initial"]["median"].predict(ip.inputs(members, "median"))
        raw_metrics[
            "initial_classification" if classification else "initial_duration"
        ] = score_channel(rows, point, b, classification)
    members = [r for r in creations if r["masks"]["classification"]]
    operational_probability = baseline["initial"]["operational"].predict_proba(
        ip.inputs(members, "operational")
    )[:, 1]
    operational_reference = {
        "classification": ev.summary(
            [evaluation_record(r, creation=True) for r in members],
            probability=operational_probability,
        )
    }
    common = [
        r
        for r in creations
        if r["masks"]["delay_regression"] and ip.operational_delay(r["x"]) is not None
    ]
    if common:
        op = [ip.operational_delay(r["x"]) for r in common]
        ml = initial.regressor.predict(ip.inputs(common, initial.regressor_name))
        common_rows = [
            evaluation_record(r, r["label"]["delay_minutes"], True) for r in common
        ]
        operational_reference["duration_common_subset"] = {
            "operational": ev.summary(common_rows, duration=op),
            "candidate_raw_diagnostic": ev.summary(common_rows, duration=ml),
            "fraction_of_completed_late": len(common)
            / sum(r["masks"]["delay_regression"] for r in creations),
        }
    for task in ("classification", "pre", "post"):
        classification = task == "classification"
        idx = [i for i, r in enumerate(rolling) if rp.included(r, task)]
        members = [rolling[i] for i in idx]
        rows = [evaluation_record(r, r["target"]["target_minutes"]) for r in members]
        b = rp.predict_model(baseline["rolling"][task], members, task)
        point = rp.predict_model(model.models[task], members, task)
        if classification:
            logits = np.log(
                np.clip(point, 1e-6, 1 - 1e-6) / np.clip(1 - point, 1e-6, 1)
            )
            point = model.calibrator.predict_proba(logits.reshape(-1, 1))[:, 1]
        name = "rolling_classification" if classification else task + "_duration"
        raw_metrics[name] = score_channel(rows, point, b, classification)
        use = [
            j
            for j, i in enumerate(idx)
            if (
                rp_outputs[i]["probability_late"] is not None
                if classification
                else rp_outputs[i]["duration_interval_minutes"] is not None
            )
        ]
        selected = [rows[j] for j in use]
        intervals = (
            None
            if classification
            else [rp_outputs[idx[j]]["duration_interval_minutes"] for j in use]
        )
        channels[name] = score_channel(
            selected, point[use], b[use], classification, intervals
        )
        selections[name] = (selected, point[use], b[use], intervals)
    for regime in ("pre", "post"):
        idx = [i for i, r in enumerate(rolling) if r["x"]["regime"] == regime]
        members = [rolling[i] for i in idx]
        w = rp.weights(members)
        available[regime] = {
            "probability": float(
                np.average(
                    [rp_outputs[i]["probability_late"] is not None for i in idx],
                    weights=w,
                )
            ),
            "duration": float(
                np.average(
                    [
                        rp_outputs[i]["duration_interval_minutes"] is not None
                        for i in idx
                    ],
                    weights=w,
                )
            ),
            "missions": len({tuple(r["key"]) for r in members}),
            "snapshots": len(idx),
            "statuses": dict(Counter(rp_outputs[i]["status"] for i in idx)),
        }
    for name, (rows, point, b, intervals) in selections.items():
        classification = name.endswith("classification")
        for key in ("profile", "urgent", "cold", "phase"):
            expected = {
                "profile": ["regular", "pressure", "perturbed"],
                "urgent": [0, 1],
                "cold": [0, 1],
            }
            for value in expected.get(key, sorted({r[key] for r in rows})):
                idx = [i for i, r in enumerate(rows) if r[key] == value]
                selected = [rows[i] for i in idx]
                bounds = None if intervals is None else [intervals[i] for i in idx]
                m = ev.summary(
                    selected,
                    probability=point[idx] if classification else None,
                    duration=None if classification else point[idx],
                    intervals=bounds,
                    baseline=b[idx],
                )
                m.update(
                    channel=name,
                    required=key != "phase",
                    sufficient=ev.sufficient(m, classification),
                )
                segments[f"{name}|{key}={value}"] = m
    promotion = ev.gates(channels, segments, available, True)
    quality = json.loads(
        (repo / "reports/quality-m03-final-20261015/quality.json").read_text()
    )
    promotion["checks"]["quality"] = quality["passed"]
    promotion["failed"] = [k for k, v in promotion["checks"].items() if not v]
    promotion["eligible"] = all(promotion["checks"].values())
    compressed_records(
        out / "test-predictions.jsonl.gz",
        (
            [
                {
                    "stage": "initial",
                    "snapshot": r["observation"],
                    "truth": r["label"],
                    "prediction": p,
                }
                for r, p in zip(creations, cp)
            ]
            + [
                {
                    "stage": "rolling",
                    "snapshot": r["observation"],
                    "creation_snapshot": r["creation"],
                    "truth": r["target"],
                    "prediction": p,
                }
                for r, p in zip(rolling, rp_outputs)
            ]
        ),
    )
    report = {
        "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_sha256": registry.sha256(out / "freeze.json"),
        "policy": ev.POLICY,
        "candidate_sha256": {
            p: sha
            for p, sha in frozen["sha256"].items()
            if p.endswith("predictor.joblib")
        },
        "test_consumed": True,
        "test_groups": sorted(groups),
        "test_runs": len(provenance),
        "provenance": provenance,
        "initial_missions": len(creations),
        "sampled_rolling": len(rolling),
        "native_rolling": sum(p["native_rolling"] for p in provenance),
        "censored_initial": sum(r["masks"]["censored"] for r in creations),
        "channels_with_policy": channels,
        "raw_diagnostic_only": raw_metrics,
        "operational_initial_reference": operational_reference,
        "segments": segments,
        "availability": available,
        "promotion": promotion,
        "artifacts": {
            "test-predictions.jsonl.gz": registry.sha256(
                out / "test-predictions.jsonl.gz"
            )
        },
    }
    write_json(out / "report.json", report)
    registry_path = repo / "models/registry-v1.json"
    state = (
        json.loads(registry_path.read_text())
        if registry_path.exists()
        else registry.empty_registry()
    )
    for name, path in [
        ("m01-v1", "reports/m01-v1/initial_predictor.joblib"),
        ("m02-v1", "reports/m02-v1/rolling_predictor.joblib"),
    ]:
        entry = {
            "artifact": {"path": path, "sha256": registry.sha256(repo / path)},
            "evaluation": {
                "path": str((out / "report.json").relative_to(repo)),
                "sha256": registry.sha256(out / "report.json"),
            },
            "references": {
                "protocol": {
                    "path": "docs/protocollo-m03-v1.md",
                    "sha256": registry.sha256(repo / "docs/protocollo-m03-v1.md"),
                },
                "freeze": {
                    "path": str((out / "freeze.json").relative_to(repo)),
                    "sha256": registry.sha256(out / "freeze.json"),
                },
            },
            "status": (
                "eligible_pending_manual_approval"
                if promotion["eligible"]
                else "evaluated_not_eligible"
            ),
            "eligibility_scope": "complete_initial_and_rolling_pipeline",
            "dependencies": ["m01-v1"] if name == "m02-v1" else [],
        }
        state = registry.register_candidate(state, name, entry, repo)
    registry.write_registry(repo / "models/registry-v1.json", state)
    print(
        json.dumps(
            {"channels": channels, "availability": available, "promotion": promotion}
        ),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "evaluate"])
    parser.add_argument("--archives", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[1]
    if args.action == "freeze":
        freeze(repo, args.output)
    else:
        if args.archives is None:
            parser.error("--archives is required for evaluate")
        evaluate(repo, args.output, args.archives)


if __name__ == "__main__":
    main()
