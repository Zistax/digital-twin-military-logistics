import hashlib
import json

import joblib
import numpy as np
import pytest

from logistics import initial_prediction as ip
from logistics.batch import make_plan


def observation():
    return {
        "feature_version": "creation-v1",
        "observed_s": 0,
        "simulation_id": "s",
        "mission_id": "m",
        "features": {
            "start_s": 0,
            "deadline_s": 3600,
            "estimated_duration_s": 1800,
            "deadline_source": "observable_estimate",
            "urgent": False,
            "free_vehicles": 10,
            "origin_id": "a",
            "destination_id": "b",
            "lines": [
                {
                    "cold": False,
                    "requested": 10,
                    "minimum": 8,
                    "available_origin": 5,
                    "stock_destination": 2,
                    "kg": "2",
                    "m3": ".1",
                }
            ],
        },
    }


def row(i, split="training", group=None):
    late = i % 2 == 0
    label = {
        "late": late,
        "eligible": True,
        "status": "reached",
        "quota_censored": False,
        "delay_minutes": float(10 + i) if late else 0.0,
    }
    return {
        "key": ("s", str(i)),
        "group": group or f"g{i//10}",
        "split": split,
        "profile": "regular",
        "x": ip.features(observation()),
        "label": label,
        "masks": ip.creation_masks(label),
    }


def training():
    return [row(i) for i in range(60)]


def calibration():
    return [row(i, "calibration", f"c{i//10}") for i in range(20)]


def test_allowlist_and_operational_missing():
    obs = observation()
    baseline = ip.features(obs)
    obs.update({"late": True, "quota_reached_s": 99999, "simulation_id": "future"})
    obs["features"]["future_weather"] = 999
    assert ip.features(obs) == baseline
    assert baseline["shortage_minimum"] == 3
    assert ip.operational_delay(baseline) == 0
    obs["features"]["estimated_duration_s"] = None
    assert ip.operational_delay(ip.features(obs)) is None


@pytest.mark.parametrize(
    "mutation",
    [
        lambda o: o.update(feature_version="rolling-v1"),
        lambda o: o.update(observed_s=1),
        lambda o: o["features"].update(deadline_s=0),
        lambda o: o["features"].update(estimated_duration_s=float("nan")),
        lambda o: o["features"].update(lines=[]),
        lambda o: o["features"].update(free_vehicles=-1),
        lambda o: o["features"]["lines"][0].update(kg="nan"),
    ],
)
def test_invalid_creation_rejected(mutation):
    obs = observation()
    mutation(obs)
    with pytest.raises(ValueError):
        ip.features(obs)


def test_folds_keep_paired_profiles_and_selection_rejects_calibration():
    rows = training()
    f = ip.folds(rows)
    assert len(set(f)) == 6
    for group in {r["group"] for r in rows}:
        assert len({f[i] for i, r in enumerate(rows) if r["group"] == group}) == 1
    with pytest.raises(ValueError, match="training only"):
        ip.oof_predictions(rows + calibration())


def test_oof_refits_inside_group_folds(monkeypatch):
    rows = training()
    original = ip.estimator
    seen = []

    def spy(name, regression=False):
        model = original(name, regression)
        fit = model.fit

        def checked(x, y):
            # Six held-out missions in this target must never be seen in fit.
            seen.append((name, regression, len(y)))
            return fit(x, y)

        model.fit = checked
        return model

    monkeypatch.setattr(ip, "estimator", spy)
    p, d, _ = ip.oof_predictions(rows)
    assert len(seen) == 36
    assert {n for _, reg, n in seen if not reg} == {50}
    assert {n for _, reg, n in seen if reg} == {25}
    assert all(np.isfinite(v).all() for v in [*p.values(), *d.values()])


def test_censoring_masks_never_impute_duration():
    r = row(0)
    r["label"].update(status="open", quota_censored=True, delay_minutes=None)
    masks = ip.creation_masks(r["label"])
    assert masks == {
        "classification": True,
        "delay_regression": False,
        "censored": True,
    }
    r["label"]["late"] = None
    assert not ip.creation_masks(r["label"])["classification"]


def test_final_fit_prediction_roundtrip_and_abstention(tmp_path):
    model = ip.fit_final(training(), calibration(), "logistic", "median")
    out = model.predict(observation())
    assert 0 <= out["probability_late"] <= 1
    assert out["conditional_delay_minutes"] == 39
    assert out["interval"] is None
    path = tmp_path / "model.joblib"
    joblib.dump(model, path)
    assert joblib.load(path).predict(observation()) == out
    bad = observation()
    bad["features"]["origin_id"] = "unseen"
    assert model.predict(bad)["status"] == "abstain"
    bad = observation()
    bad["features"]["free_vehicles"] = 999
    assert model.predict(bad)["status"] == "abstain"
    assert model.predict({})["reasons"] == ["invalid_creation_observation"]
    model.support[ip.segment(ip.features(observation()))]["censored_rate"] = 0.5
    out = model.predict(observation())
    assert out["status"] == "probability_only"
    assert out["conditional_delay_minutes"] is None


def test_operational_prediction_and_split_guards():
    model = ip.fit_final(training(), calibration(), "operational", "operational")
    assert model.predict(observation())["conditional_delay_minutes"] == 0
    with pytest.raises(ValueError, match="invalid final fit"):
        ip.fit_final(training(), training(), "logistic", "median")
    cal = calibration()
    cal[0]["group"] = "g0"
    with pytest.raises(ValueError, match="leakage"):
        ip.fit_final(training(), cal, "logistic", "median")


def test_metrics_include_missing_duration_coverage_and_single_class():
    assert ip.classification_metrics([], []) == {"n": 0}
    assert ip.classification_metrics([1, 1], [0.2, 0.8])["roc_auc"] is None
    assert ip.classification_metrics([0, 1], [0.1, 0.9])["roc_auc"] == 1
    assert ip.delay_metrics([10, 20], [None, 21])["coverage"] == 0.5
    assert ip.delay_metrics([10], [None]) == {"n": 0, "coverage": 0.0}


@pytest.fixture
def dataset(tmp_path, monkeypatch):
    plan = make_plan()
    monkeypatch.setattr(ip, "PLAN_SHA", plan["plan_sha256"])
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    split = {
        "plan_sha256": plan["plan_sha256"],
        "sets": {"training": [], "calibration": []},
    }
    for run in plan["runs"]:
        if run["split"] == "test":
            continue  # No test directory exists: opening any test table fails.
        relative = f"bundles/{run['simulation_id']}-attempt-2"
        folder = tmp_path / relative
        folder.mkdir(parents=True)
        obs = observation()
        obs["simulation_id"] = run["simulation_id"]
        label = row(0)["label"] | {
            "simulation_id": run["simulation_id"],
            "mission_id": "m",
        }
        files = {}
        for name, data in [("observations.jsonl", obs), ("labels.jsonl", label)]:
            content = (json.dumps(data) + "\n").encode()
            (folder / name).write_bytes(content)
            files[name] = {"rows": 1, "sha256": hashlib.sha256(content).hexdigest()}
        manifest = {"schema_version": 4, "group_id": run["group_id"], "files": files}
        content = json.dumps(manifest).encode()
        (folder / "manifest.json").write_bytes(content)
        split["sets"][run["split"]].append(
            run
            | {
                "bundle": relative,
                "valid": True,
                "manifest_sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    (tmp_path / "split_manifest.json").write_text(json.dumps(split))
    return tmp_path


def test_loader_reads_accepted_retry_and_never_test(dataset):
    rows, provenance = ip.load_creation(dataset)
    assert len(rows) == len(provenance) == 72
    assert {r["split"] for r in rows} == {"training", "calibration"}


def test_loader_rejects_tampered_table_and_manifest(dataset):
    table = next(dataset.glob("bundles/*/observations.jsonl"))
    table.write_text(table.read_text() + "\n")
    with pytest.raises(ValueError, match="table checksum"):
        ip.load_creation(dataset)
    manifest = table.parent / "manifest.json"
    manifest.write_text(manifest.read_text() + " ")
    with pytest.raises(ValueError, match="manifest checksum"):
        ip.load_creation(dataset)


def test_loader_rejects_tampered_plan(dataset):
    p = dataset / "plan.json"
    plan = json.loads(p.read_text())
    plan["generation_days"] = 1
    p.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="checksum"):
        ip.load_creation(dataset)
