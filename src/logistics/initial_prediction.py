"""Creation-time predictors; training and final-test access stay separate."""

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    mean_absolute_error,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .training_masks import creation_masks
from .batch import validate_plan

PLAN_SHA = "0b947c221014b117cf6bb2f3b3f1116d5aff59e74258fe1a9a3e60d8a663dcd0"
CLASSIFIERS = ("prevalence", "operational", "logistic", "boosting")
REGRESSORS = ("median", "boosting")


def features(observation):
    """Explicit allowlist: outcome and simulation identifiers cannot enter X."""
    if observation.get("feature_version") != "creation-v1":
        raise ValueError("expected creation-v1")
    f = observation["features"]
    if observation["observed_s"] != f["start_s"]:
        raise ValueError("not a creation-time observation")
    allowance = (f["deadline_s"] - f["start_s"]) / 60
    estimate = f["estimated_duration_s"]
    if allowance <= 0 or not isinstance(f["urgent"], bool):
        raise ValueError("invalid creation features")
    if estimate is not None and (not math.isfinite(estimate) or estimate < 0):
        raise ValueError("invalid estimate")
    lines = f["lines"]
    if not lines or f["free_vehicles"] < 0:
        raise ValueError("invalid load/fleet")
    result = {
        "origin": f["origin_id"],
        "destination": f["destination_id"],
        "urgent": int(f["urgent"]),
        "cold": int(any(line["cold"] for line in lines)),
        "estimate_missing": int(estimate is None),
        "estimate_reason": f.get("estimate_unavailable_reason") or "available",
        "deadline_source": f["deadline_source"],
        "allowance_minutes": allowance,
        "estimate_minutes": estimate / 60 if estimate is not None else 0.0,
        "slack_minutes": allowance - estimate / 60 if estimate is not None else 0.0,
        "free_vehicles": f["free_vehicles"],
        "elapsed_days": f["start_s"] / 86400,
        "hour_sin": math.sin(2 * math.pi * f["start_s"] / 86400),
        "hour_cos": math.cos(2 * math.pi * f["start_s"] / 86400),
        "lines": len(lines),
    }
    for name in ("requested", "minimum", "available_origin", "stock_destination"):
        result[name] = sum(line[name] for line in lines)
    for name in ("kg", "m3"):
        result[name] = sum(float(line[name]) * line["requested"] for line in lines)
    result["shortage_minimum"] = sum(
        max(0, line["minimum"] - line["available_origin"]) for line in lines
    )
    result["shortage_requested"] = sum(
        max(0, line["requested"] - line["available_origin"]) for line in lines
    )
    if any(
        not math.isfinite(v)
        or (k not in {"slack_minutes", "hour_sin", "hour_cos"} and v < 0)
        for k, v in result.items()
        if isinstance(v, (int, float))
    ):
        raise ValueError("invalid numeric features")
    return result


def segment(x):
    return f"urgent={x['urgent']}|cold={x['cold']}|missing={x['estimate_missing']}"


def operational_delay(x):
    return (
        None
        if x["estimate_missing"]
        else max(0.0, x["estimate_minutes"] - x["allowance_minutes"])
    )


def load_creation(root):
    """Read only training/calibration paths named by the frozen D03 plan."""
    root = Path(root)
    plan = json.loads((root / "plan.json").read_text())
    if plan["plan_sha256"] != PLAN_SHA:
        raise ValueError("unexpected D03 plan")
    validate_plan(plan)
    split_manifest = json.loads((root / "split_manifest.json").read_text())
    if split_manifest["plan_sha256"] != PLAN_SHA:
        raise ValueError("split manifest mismatch")
    accepted = {
        r["simulation_id"]: r
        for name in ("training", "calibration")
        for r in split_manifest["sets"][name]
    }
    rows, provenance = [], []
    for run in plan["runs"]:
        if run["split"] == "test":
            continue
        if run["split"] not in {"training", "calibration"}:
            raise ValueError("invalid split")
        record = accepted[run["simulation_id"]]
        if (
            record["split"] != run["split"]
            or record["group_id"] != run["group_id"]
            or record["valid"] is not True
        ):
            raise ValueError("accepted run mismatch")
        folder = root / record["bundle"]
        if not folder.resolve().is_relative_to(root.resolve()):
            raise ValueError("bundle outside dataset")
        manifest_bytes = (folder / "manifest.json").read_bytes()
        if hashlib.sha256(manifest_bytes).hexdigest() != record["manifest_sha256"]:
            raise ValueError("manifest checksum mismatch")
        manifest = json.loads(manifest_bytes)
        if manifest["group_id"] != run["group_id"] or manifest["schema_version"] != 4:
            raise ValueError("manifest/run mismatch")
        tables = {}
        for name in ("observations.jsonl", "labels.jsonl"):
            data = (folder / name).read_bytes()
            meta = manifest["files"][name]
            if hashlib.sha256(data).hexdigest() != meta["sha256"]:
                raise ValueError("table checksum mismatch")
            parsed = [json.loads(line) for line in data.splitlines()]
            if len(parsed) != meta["rows"]:
                raise ValueError("table count mismatch")
            keys = [(r["simulation_id"], r["mission_id"]) for r in parsed]
            if len(set(keys)) != len(keys):
                raise ValueError("duplicate mission")
            if any(k[0] != run["simulation_id"] for k in keys):
                raise ValueError("simulation mismatch")
            tables[name] = dict(zip(keys, parsed))
        if tables["observations.jsonl"].keys() != tables["labels.jsonl"].keys():
            raise ValueError("unpaired labels")
        for key, obs in tables["observations.jsonl"].items():
            label = tables["labels.jsonl"][key]
            rows.append(
                {
                    "key": key,
                    "group": run["group_id"],
                    "split": run["split"],
                    "profile": run["profile"],
                    "x": features(obs),
                    "observation": obs,
                    "label": label,
                    "masks": creation_masks(label),
                }
            )
        provenance.append(
            {
                "simulation_id": run["simulation_id"],
                "group": run["group_id"],
                "split": run["split"],
                "files": {n: manifest["files"][n] for n in tables},
            }
        )
    groups = {
        s: {r["group"] for r in rows if r["split"] == s}
        for s in ("training", "calibration")
    }
    if (
        len(provenance) != 72
        or len(groups["training"]) != 18
        or len(groups["calibration"]) != 6
    ):
        raise ValueError("incomplete D03 development data")
    if groups["training"] & groups["calibration"]:
        raise ValueError("split leakage")
    return rows, provenance


def folds(rows):
    groups = sorted(
        {r["group"] for r in rows},
        key=lambda g: hashlib.sha256(("m01-v1|" + g).encode()).digest(),
    )
    assignment = {g: i % 6 for i, g in enumerate(groups)}
    return np.array([assignment[r["group"]] for r in rows])


def inputs(rows, name):
    if name == "operational":
        return [
            {k: r["x"][k] for k in ("slack_minutes", "estimate_missing")} for r in rows
        ]
    return [r["x"] for r in rows]


def estimator(name, regression=False):
    if regression:
        model = (
            DummyRegressor(strategy="median")
            if name == "median"
            else HistGradientBoostingRegressor(
                loss="absolute_error",
                max_iter=80,
                max_depth=3,
                l2_regularization=1,
                early_stopping=False,
                random_state=1401,
            )
        )
    else:
        if name == "prevalence":
            model = DummyClassifier(strategy="prior")
        elif name == "boosting":
            model = HistGradientBoostingClassifier(
                max_iter=80,
                max_depth=3,
                l2_regularization=1,
                early_stopping=False,
                random_state=1401,
            )
        else:
            model = LogisticRegression(C=1, max_iter=2000, random_state=1401)
    return make_pipeline(DictVectorizer(sparse=False), StandardScaler(), model)


def classification_metrics(y, p):
    y, p = np.asarray(y), np.asarray(p)
    if len(y) == 0:
        return {"n": 0}
    bins = np.minimum((p * 10).astype(int), 9)
    ece = sum(
        abs(float(np.mean(y[bins == b])) - float(np.mean(p[bins == b])))
        * np.mean(bins == b)
        for b in set(bins)
    )
    both = len(set(y)) == 2
    return {
        "n": len(y),
        "late_rate": float(np.mean(y)),
        "brier": float(brier_score_loss(y, p)),
        "ece": float(ece),
        "roc_auc": float(roc_auc_score(y, p)) if both else None,
        "pr_auc": float(average_precision_score(y, p)) if both else None,
    }


def delay_metrics(y, p):
    pairs = [(a, b) for a, b in zip(y, p) if b is not None and np.isfinite(b)]
    if not pairs:
        return {"n": 0, "coverage": 0.0}
    a, b = np.array(pairs).T
    error = abs(a - b)
    return {
        "n": len(a),
        "coverage": len(a) / len(y),
        "mae_minutes": float(mean_absolute_error(a, b)),
        "p90_absolute_error_minutes": float(np.quantile(error, 0.9)),
        "fraction_error_over_1_day": float(np.mean(error > 1440)),
    }


def oof_predictions(rows):
    """All preprocessing is fitted inside each group fold, including dummies."""
    if {r["split"] for r in rows} != {"training"}:
        raise ValueError("selection accepts training only")
    fold = folds(rows)
    predictions = {name: np.full(len(rows), np.nan) for name in CLASSIFIERS}
    delays = {name: np.full(len(rows), np.nan) for name in REGRESSORS}
    for i in range(6):
        train = [r for j, r in enumerate(rows) if fold[j] != i]
        valid = [r for j, r in enumerate(rows) if fold[j] == i]
        for name in CLASSIFIERS:
            fit = [r for r in train if r["masks"]["classification"]]
            model = estimator(name)
            model.fit(inputs(fit, name), [r["label"]["late"] for r in fit])
            predictions[name][fold == i] = model.predict_proba(inputs(valid, name))[
                :, 1
            ]
        for name in REGRESSORS:
            fit = [r for r in train if r["masks"]["delay_regression"]]
            model = estimator(name, regression=True)
            model.fit(inputs(fit, name), [r["label"]["delay_minutes"] for r in fit])
            delays[name][fold == i] = np.maximum(0, model.predict(inputs(valid, name)))
    return predictions, delays, fold


@dataclass
class InitialPredictor:
    classifier_name: str
    regressor_name: str
    classifier: object
    regressor: object
    calibrator: object
    support: dict
    ranges: dict
    categories: dict

    def predict(self, observation):
        """Return explicit abstention, never reinterpret censored duration as zero."""
        output = {
            "model_version": "m01-v1",
            "domain": "synthetic_D03_v1_only",
            "stage": "creation",
            "probability_late": None,
            "conditional_delay_minutes": None,
            "duration_target": "median_delay_given_late_and_quota_reached",
            "interval": None,
            "status": "abstain",
            "reasons": [],
        }
        try:
            x = features(observation)
        except (KeyError, TypeError, ValueError, OverflowError):
            output["reasons"] = ["invalid_creation_observation"]
            return output
        unsupported = any(x[k] not in values for k, values in self.categories.items())
        outside = any(
            not (lo - 1e-8 <= x[k] <= hi + 1e-8) for k, (lo, hi) in self.ranges.items()
        )
        support = self.support.get(segment(x), {})
        output["training_segment"] = support
        if (
            unsupported
            or outside
            or support.get("n", 0) < 30
            or support.get("groups", 0) < 3
        ):
            output["reasons"] = ["outside_training_support"]
            return output
        p = self.classifier.predict_proba(inputs([{"x": x}], self.classifier_name))[
            :, 1
        ]
        logit = np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1))
        output["probability_late"] = float(
            self.calibrator.predict_proba(logit.reshape(-1, 1))[0, 1]
        )
        output["status"] = "probability_only"
        if (
            support["censored_rate"] > 0.4
            or support["delay_n"] < 30
            or support["delay_groups"] < 3
        ):
            output["reasons"] = ["insufficient_uncensored_duration_support"]
            return output
        if self.regressor_name == "operational":
            delay = operational_delay(x)
        else:
            delay = max(0.0, float(self.regressor.predict([x])[0]))
        if delay is None:
            output["reasons"] = ["operational_estimate_unavailable"]
            return output
        output["conditional_delay_minutes"] = delay
        output["status"] = "available_conditional_duration"
        output["reasons"] = [
            "duration_excludes_censored_outcomes",
            "synthetic_domain_only",
        ]
        return output


def fit_final(training, calibration, classifier_name, regressor_name):
    if {r["split"] for r in training} != {"training"} or {
        r["split"] for r in calibration
    } != {"calibration"}:
        raise ValueError("invalid final fit split")
    if {r["group"] for r in training} & {r["group"] for r in calibration}:
        raise ValueError("calibration leakage")
    fit = [r for r in training if r["masks"]["classification"]]
    clf = estimator(classifier_name)
    clf.fit(inputs(fit, classifier_name), [r["label"]["late"] for r in fit])
    cal = [r for r in calibration if r["masks"]["classification"]]
    p = clf.predict_proba(inputs(cal, classifier_name))[:, 1]
    logit = np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1))
    sigmoid = LogisticRegression(C=1, random_state=1401).fit(
        logit.reshape(-1, 1), [r["label"]["late"] for r in cal]
    )
    delay_fit = [r for r in training if r["masks"]["delay_regression"]]
    reg = None
    if regressor_name != "operational":
        reg = estimator(regressor_name, regression=True)
        reg.fit(
            inputs(delay_fit, regressor_name),
            [r["label"]["delay_minutes"] for r in delay_fit],
        )
    support = {}
    for key in sorted({segment(r["x"]) for r in training}):
        members = [r for r in training if segment(r["x"]) == key]
        reached = [r for r in members if r["masks"]["delay_regression"]]
        support[key] = {
            "n": len(members),
            "groups": len({r["group"] for r in members}),
            "censored_rate": sum(r["masks"]["censored"] for r in members)
            / len(members),
            "delay_n": len(reached),
            "delay_groups": len({r["group"] for r in reached}),
        }
    keys = training[0]["x"]
    ranges = {
        k: (min(r["x"][k] for r in training), max(r["x"][k] for r in training))
        for k in keys
        if not isinstance(training[0]["x"][k], str)
    }
    categories = {
        k: sorted({r["x"][k] for r in training})
        for k in keys
        if isinstance(training[0]["x"][k], str)
    }
    return InitialPredictor(
        classifier_name, regressor_name, clf, reg, sigmoid, support, ranges, categories
    )
