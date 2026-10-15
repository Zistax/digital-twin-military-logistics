from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pytest

from logistics import initial_prediction as ip
from logistics import rolling_prediction as rp


def snapshots(i=0, now=100):
    creation = {
        "feature_version": "creation-v1",
        "observed_s": 0,
        "simulation_id": "s",
        "mission_id": str(i),
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
                    "item_id": "x",
                    "cold": False,
                    "requested": 10,
                    "minimum": 8,
                    "available_origin": 10,
                    "stock_destination": 2,
                    "kg": "2",
                    "m3": ".1",
                }
            ],
        },
    }
    obs = {
        "schema_version": 1,
        "feature_version": "rolling-v1",
        "simulation_id": "s",
        "mission_id": str(i),
        "observation_id": f"{i}:rolling:{now}",
        "observed_s": now,
        "features": {
            "status": "waiting" if now < 3600 else "en_route",
            "elapsed_s": now,
            "seconds_to_deadline": 3600 - now,
            "urgent": False,
            "recovery_statuses": [],
            "lines": [
                {
                    "item_id": "x",
                    "minimum": 8,
                    "accepted": now // 1000,
                    "reserved": 6,
                    "unusable_inspected": 0,
                }
            ],
        },
    }
    return creation, obs


def dataset(split="training", prefix="g"):
    rows, creations = [], []
    for i in range(60):
        creation, _ = snapshots(i)
        late = i % 2 == 0
        label = {
            "eligible": True,
            "late": late,
            "quota_censored": False,
            "status": "reached",
            "delay_minutes": float(100 + i) if late else 0,
        }
        creations.append(
            {
                "key": ["s", str(i)],
                "group": f"{prefix}{i//10}",
                "split": split,
                "observation": creation,
                "x": ip.features(creation),
                "label": label,
                "masks": ip.creation_masks(label),
            }
        )
        for now in ([100, 200, 3700, 4000] if late else [100, 200]):
            creation, obs = snapshots(i, now)
            x = rp.rolling_features(creation, obs)
            value = (
                (100 + i if now < 3600 else 100 + i - (now - 3600) / 60)
                if late
                else None
            )
            target = {
                "eligible": True,
                "late": late,
                "target_kind": (
                    "delay_if_late" if now < 3600 else "remaining_after_deadline"
                ),
                "target_minutes": value,
                "quota_censored": False,
            }
            rows.append(
                {
                    "key": ["s", str(i)],
                    "group": f"{prefix}{i//10}",
                    "split": split,
                    "x": x,
                    "target": target,
                    "creation": creation,
                    "observation": obs,
                }
            )
    return rows, creations


@pytest.fixture
def predictor():
    train, ct = dataset()
    cal, cc = dataset("calibration", "c")
    # Distinct mission IDs across simulations are legal; groups define split isolation.
    initial = ip.fit_final(ct, cc, "logistic", "median")
    model = rp.fit_predictor(
        train,
        cal,
        {"classification": "logistic", "pre": "median", "post": "median"},
        initial,
    )
    return rp.calibrate_intervals(model, cal, cc)


def test_live_features_allowlist_and_deadline_boundary():
    creation, obs = snapshots()
    x = rp.rolling_features(creation, obs)
    creation["ground_truth"] = {"future_damage": 999}
    assert rp.rolling_features(creation, obs) == x
    assert "ground_truth" not in x
    _, boundary = snapshots(now=3600)
    assert rp.rolling_features(creation, boundary)["regime"] == "post"
    assert x["initial_free_vehicles"] == 10
    assert x["deficit_units"] == 8


@pytest.mark.parametrize(
    "mutation",
    [
        lambda o: o.update(feature_version="creation-v1"),
        lambda o: o.update(observation_id=""),
        lambda o: o.update(mission_id="other"),
        lambda o: o.update(observed_s=-1),
        lambda o: o["features"].update(elapsed_s=99),
        lambda o: o["features"].update(urgent=True),
        lambda o: o["features"].update(future_damage=999),
        lambda o: o["features"].update(lines=[]),
        lambda o: o["features"]["lines"][0].update(minimum=9),
        lambda o: o["features"]["lines"][0].update(reserved=-1),
        lambda o: o["features"]["lines"][0].update(accepted=1.5),
        lambda o: o["features"]["lines"][0].update(future_damage=1),
    ],
)
def test_invalid_or_future_observation_rejected(mutation):
    creation, obs = snapshots()
    mutation(obs)
    with pytest.raises(ValueError):
        rp.rolling_features(creation, obs)


def test_mission_weights_and_censor_masks():
    rows, _ = dataset()
    w = rp.weights(rows)
    for mission in {tuple(r["key"]) for r in rows}:
        for regime in ("pre", "post"):
            idx = [
                i
                for i, r in enumerate(rows)
                if tuple(r["key"]) == mission and r["x"]["regime"] == regime
            ]
            if idx:
                assert sum(w[idx]) == pytest.approx(1)
    r = deepcopy(rows[0])
    r["target"].update(quota_censored=True, target_minutes=None)
    assert rp.included(r, "classification")
    assert not rp.included(r, "pre")


def test_group_interval_finite_sample_rank_and_missing_groups():
    errors = [(f"g{i}", float(i)) for i in range(6)] + [("g0", 7.0)]
    interval = rp.GroupInterval.calibrate(errors)
    assert interval.radius == 7
    assert interval.groups == 6
    assert interval.bounds(2) == [0, 9]
    assert rp.GroupInterval.calibrate(errors[:2]).bounds(2) is None
    with pytest.raises(ValueError):
        rp.GroupInterval.calibrate([("g", float("nan"))])


def test_weighted_scaler_keeps_constant_columns_finite():
    values = np.array([[1.0, 2.0], [1.0, 6.0], [1.0, 10.0]])
    sample_weight = np.array([0.1, 0.2, 0.7])
    scaler = rp.MissionScaler().fit(values, sample_weight=sample_weight)
    transformed = scaler.transform(values)
    assert np.isfinite(transformed).all()
    assert scaler.scale_[0] == 1
    assert np.average(transformed[:, 1], weights=sample_weight) == pytest.approx(
        0, abs=1e-12
    )


def test_pre_post_probabilities_and_arithmetic(predictor, tmp_path):
    for now in (100, 3700):
        creation, obs = snapshots(now=now)
        p = predictor.predict(creation, obs)
        assert p["status"] == "available_conditional_duration"
        assert p["observed_s"] == now
        assert p["duration_interval_minutes"] is not None
        if now < 3600:
            assert 0 <= p["probability_late"] <= 1
            assert p["remaining_minutes"] is None
        else:
            assert p["probability_late"] is None
            assert p["conditional_delay_minutes"] is None
            assert p["final_delay_minutes"] == pytest.approx(
                p["accumulated_delay_minutes"] + p["remaining_minutes"]
            )
            assert (
                p["final_delay_interval_minutes"][0] >= p["accumulated_delay_minutes"]
            )
            assert p["final_delay_interval_minutes"][1] == pytest.approx(
                p["accumulated_delay_minutes"] + p["duration_interval_minutes"][1]
            )
    path = tmp_path / "model.joblib"
    joblib.dump(predictor, path)
    assert joblib.load(path).predict(creation, obs) == p


def test_terminal_invalid_and_outside_domain(predictor):
    creation, obs = snapshots()
    obs["features"]["lines"][0]["accepted"] = 8
    assert predictor.predict(creation, obs)["reasons"] == ["quota_reached"]
    obs["features"]["status"] = "cancelled"
    assert predictor.predict(creation, obs)["status"] == "stopped"
    assert predictor.predict({}, {})["reasons"] == ["invalid_rolling_observation"]
    creation, obs = snapshots()
    obs["features"]["status"] = "never_observed"
    assert predictor.predict(creation, obs)["status"] == "abstain"
    creation, obs = snapshots(now=100000)
    obs["features"]["lines"][0]["accepted"] = 1
    assert predictor.predict(creation, obs)["status"] == "abstain"


def test_support_abstention_and_missing_interval(predictor):
    creation, obs = snapshots()
    x = rp.rolling_features(creation, obs)
    support = predictor.support[rp.segment(x)]
    support["censored_rate"] = 0.5
    p = predictor.predict(creation, obs)
    assert p["status"] == "probability_only" and p["duration_interval_minutes"] is None
    support["missions"] = 2
    assert predictor.predict(creation, obs)["status"] == "abstain"
    support["missions"], support["censored_rate"] = 60, 0
    predictor.intervals["pre"] = rp.GroupInterval(None, 0)
    assert (
        "insufficient_interval_calibration_groups"
        in predictor.predict(creation, obs)["reasons"]
    )
    result = predictor.predict_creation(creation)
    assert result["interval"] is not None
    predictor.intervals["initial"] = rp.GroupInterval(None, 0)
    assert (
        "insufficient_interval_calibration_groups"
        in predictor.predict_creation(creation)["reasons"]
    )


def test_metrics_and_group_oof_do_not_fit_calibration():
    rows, _ = dataset()
    assert rp.metrics([], [], "pre")["missions"] == 0
    assert len(rp.predict_model(None, [], "pre")) == 0
    scores, values = rp.oof(rows)
    assert scores["classification"]["logistic"]["missions"] == 60
    assert scores["post"]["boosting"]["missions"] == 30
    assert set(scores) == {"classification", "pre", "post"}
    assert np.isfinite(values["classification"]["boosting"][:2]).all()
    with pytest.raises(ValueError, match="training only"):
        rp.oof([dict(r, split="calibration") for r in rows])
    with pytest.raises(ValueError, match="no eligible"):
        rp.fit_model([], "median", "pre")


def test_fit_split_leakage_guards(predictor):
    train, _ = dataset()
    cal, _ = dataset("calibration", "c")
    choices = {"classification": "logistic", "pre": "median", "post": "median"}
    with pytest.raises(ValueError, match="invalid fit splits"):
        rp.fit_predictor(train, train, choices, predictor.initial)
    cal[0]["group"] = "g0"
    with pytest.raises(ValueError, match="group leakage"):
        rp.fit_predictor(train, cal, choices, predictor.initial)


def test_interval_metrics_use_equal_mission_weights(predictor):
    rows, _ = dataset()
    outputs = predictor.predict_many(rows)
    result = rp.interval_metrics(rows, outputs, "pre")
    assert result["missions"] == 30
    assert 0 <= result["coverage"] <= 1
    for p in outputs:
        p["duration_interval_minutes"] = None
    assert rp.interval_metrics(rows, outputs, "pre")["coverage"] is None


def test_sampler_is_order_invariant_and_includes_first_state():
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location(
        "m02_prepare", scripts / "prepare_m02_data.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    observations = [snapshots(now=100 + i * 100)[1] for i in range(12)]
    observations[5]["features"]["status"] = "loading"
    lines = [(json.dumps(o) + "\n").encode() for o in observations]
    selected, count, _ = module.sample_observations(lines)
    reversed_selected, _, _ = module.sample_observations(reversed(lines))
    assert selected.keys() == reversed_selected.keys()
    assert observations[0]["observation_id"] in selected
    assert observations[5]["observation_id"] in selected
    assert count == 12 and len(selected) <= 6
