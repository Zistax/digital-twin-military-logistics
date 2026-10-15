"""Observable rolling predictors with mission weights and group uncertainty."""

from collections import Counter, defaultdict
from dataclasses import dataclass
import math

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from .initial_prediction import features, estimator, folds
from .training_masks import rolling_masks


class PredictionStopped(ValueError):
    """The target is no longer open; no further forecast is appropriate."""


class MissionScaler(TransformerMixin, BaseEstimator):
    """Two-pass weighted variance stays nonnegative for constant columns."""

    def fit(self, values, y=None, sample_weight=None):
        values = np.asarray(values, dtype=float)
        self.mean_ = np.average(values, axis=0, weights=sample_weight)
        variance = np.average((values - self.mean_) ** 2, axis=0, weights=sample_weight)
        self.scale_ = np.sqrt(variance)
        constant = (
            self.scale_ <= np.finfo(float).eps * np.maximum(1, abs(self.mean_)) * 16
        )
        self.scale_[constant] = 1.0
        return self

    def transform(self, values):
        return (np.asarray(values, dtype=float) - self.mean_) / self.scale_


def rolling_features(creation, observation):
    initial = features(creation)
    if (
        not isinstance(observation.get("observation_id"), str)
        or not observation["observation_id"]
    ):
        raise ValueError("missing observation identity")
    if (
        observation.get("feature_version") != "rolling-v1"
        or observation.get("schema_version") != 1
    ):
        raise ValueError("expected rolling-v1")
    if any(creation[k] != observation[k] for k in ("simulation_id", "mission_id")):
        raise ValueError("mission mismatch")
    f = observation["features"]
    if set(f) != {
        "status",
        "elapsed_s",
        "seconds_to_deadline",
        "urgent",
        "lines",
        "recovery_statuses",
    }:
        raise ValueError("unapproved rolling features")
    if f["status"] == "cancelled":
        raise PredictionStopped("cancelled")
    now = observation["observed_s"]
    original = creation["features"]
    if type(now) is not int or now < creation["observed_s"]:
        raise ValueError("invalid cutoff")
    if (
        f["elapsed_s"] != now - original["start_s"]
        or f["seconds_to_deadline"] != original["deadline_s"] - now
    ):
        raise ValueError("inconsistent rolling time")
    if type(f["urgent"]) is not bool or f["urgent"] != original["urgent"]:
        raise ValueError("inconsistent urgency")
    originals = {line["item_id"]: line for line in original["lines"]}
    lines = f["lines"]
    if len(lines) != len(originals) or {line["item_id"] for line in lines} != set(
        originals
    ):
        raise ValueError("inconsistent item lines")
    for line in lines:
        if set(line) != {
            "item_id",
            "minimum",
            "accepted",
            "unusable_inspected",
            "reserved",
        }:
            raise ValueError("unapproved line feature")
        if line["minimum"] != originals[line["item_id"]]["minimum"]:
            raise ValueError("inconsistent quota")
        if any(
            type(line[k]) is not int or line[k] < 0
            for k in ("minimum", "accepted", "unusable_inspected", "reserved")
        ):
            raise ValueError("invalid observed quantity")
    if all(line["accepted"] >= line["minimum"] for line in lines):
        raise PredictionStopped("quota_reached")
    x = {"initial_" + k: v for k, v in initial.items()}
    deficits = [max(0, line["minimum"] - line["accepted"]) for line in lines]
    x.update(
        {
            "regime": "pre" if f["seconds_to_deadline"] > 0 else "post",
            "phase": f["status"],
            "elapsed_minutes": f["elapsed_s"] / 60,
            "to_deadline_minutes": f["seconds_to_deadline"] / 60,
            "deficit_units": sum(deficits),
            "accepted_fraction": sum(
                min(line["minimum"], line["accepted"]) for line in lines
            )
            / sum(line["minimum"] for line in lines),
            "items_below_quota": sum(d > 0 for d in deficits),
            "reserved_units": sum(line["reserved"] for line in lines),
            "unusable_inspected": sum(line["unusable_inspected"] for line in lines),
            "observed_recoveries": len(f["recovery_statuses"]),
            "recovery_status": "|".join(sorted(set(f["recovery_statuses"]))) or "none",
        }
    )
    return x


def segment(x):
    return "|".join(
        str(x[k])
        for k in (
            "regime",
            "initial_urgent",
            "initial_cold",
            "initial_estimate_missing",
        )
    )


def weights(rows):
    counts = Counter((*r["key"], r["x"]["regime"]) for r in rows)
    return np.array([1 / counts[(*r["key"], r["x"]["regime"])] for r in rows])


def included(row, task):
    masks = rolling_masks(row["target"])
    if task == "classification":
        return row["x"]["regime"] == "pre" and masks["classification"]
    return row["x"]["regime"] == task and masks["duration_regression"]


def fit_model(rows, name, task):
    selected = [r for r in rows if included(r, task)]
    if not selected:
        raise ValueError("no eligible observations")
    model = estimator(name, regression=task != "classification")
    if name == "logistic":
        model.set_params(logisticregression__solver="liblinear")
    model.steps[1] = ("missionscaler", MissionScaler())
    y = [
        r["target"]["late" if task == "classification" else "target_minutes"]
        for r in selected
    ]
    w = weights(selected)
    model.fit(
        [r["x"] for r in selected],
        y,
        missionscaler__sample_weight=w,
        **{model.steps[-1][0] + "__sample_weight": w},
    )
    return model


def predict_model(model, rows, task):
    if not rows:
        return np.array([])
    x = [r["x"] for r in rows]
    if task != "classification":
        return np.maximum(0, model.predict(x))
    classes = list(model.classes_)
    return (
        model.predict_proba(x)[:, classes.index(True)]
        if True in classes
        else np.zeros(len(x))
    )


def metrics(rows, predictions, task):
    if not rows:
        return {"snapshots": 0, "missions": 0}
    y = np.array(
        [
            r["target"]["late" if task == "classification" else "target_minutes"]
            for r in rows
        ]
    )
    p, w = np.asarray(predictions), weights(rows)
    result = {
        "snapshots": len(rows),
        "missions": len({tuple(r["key"]) for r in rows}),
        "groups": len({r["group"] for r in rows}),
    }
    if task == "classification":
        bins = np.minimum((p * 10).astype(int), 9)
        result.update(
            {
                "brier": float(np.average((y - p) ** 2, weights=w)),
                "ece": float(
                    sum(
                        abs(
                            np.average(y[bins == b], weights=w[bins == b])
                            - np.average(p[bins == b], weights=w[bins == b])
                        )
                        * sum(w[bins == b])
                        / sum(w)
                        for b in set(bins)
                    )
                ),
                "roc_auc": (
                    float(roc_auc_score(y, p, sample_weight=w))
                    if len(set(y)) == 2
                    else None
                ),
                "pr_auc": (
                    float(average_precision_score(y, p, sample_weight=w))
                    if len(set(y)) == 2
                    else None
                ),
            }
        )
    else:
        result.update(
            {
                "mae_minutes": float(np.average(abs(y - p), weights=w)),
                "error_over_1_day": float(np.average(abs(y - p) > 1440, weights=w)),
            }
        )
    return result


def oof(rows):
    if {r["split"] for r in rows} != {"training"}:
        raise ValueError("selection accepts training only")
    assignments = folds(rows)
    result, scores = {}, {}
    for task, candidates in [
        ("classification", ("prevalence", "logistic", "boosting")),
        ("pre", ("median", "boosting")),
        ("post", ("median", "boosting")),
    ]:
        idx = [i for i, r in enumerate(rows) if included(r, task)]
        selected = [rows[i] for i in idx]
        values = {n: np.full(len(rows), np.nan) for n in candidates}
        for fold in range(6):
            train = [r for i, r in enumerate(rows) if assignments[i] != fold]
            valid_idx = [i for i in idx if assignments[i] == fold]
            valid = [rows[i] for i in valid_idx]
            for name in candidates:
                model = fit_model(train, name, task)
                values[name][valid_idx] = predict_model(model, valid, task)
        scores[task] = {
            name: metrics(selected, p[idx], task) for name, p in values.items()
        }
        result[task] = values
    return scores, result


@dataclass
class GroupInterval:
    radius: float | None
    groups: int
    nominal: float = 0.8

    @classmethod
    def calibrate(cls, errors, nominal=0.8):
        maxima = {}
        for group, error in errors:
            if not math.isfinite(error) or error < 0:
                raise ValueError("invalid calibration error")
            maxima[group] = max(maxima.get(group, 0), error)
        n = len(maxima)
        rank = math.ceil((n + 1) * nominal)
        radius = sorted(maxima.values())[rank - 1] if 0 < rank <= n else None
        return cls(radius, n, nominal)

    def bounds(self, point):
        if self.radius is None:
            return None
        return [max(0.0, float(point - self.radius)), float(point + self.radius)]


@dataclass
class RollingPredictor:
    models: dict
    calibrator: object
    support: dict
    ranges: dict
    categories: dict
    intervals: dict
    initial: object

    def support_reason(self, x):
        regime = x["regime"]
        if regime not in self.ranges:
            return "outside_training_support"
        if any(x[k] not in vals for k, vals in self.categories[regime].items()):
            return "outside_training_support"
        if any(
            not lo - 1e-8 <= x[k] <= hi + 1e-8
            for k, (lo, hi) in self.ranges[regime].items()
        ):
            return "outside_training_support"
        support = self.support.get(segment(x), {})
        if support.get("missions", 0) < 30 or support.get("groups", 0) < 3:
            return "insufficient_mission_support"
        return None

    def duration_supported(self, x):
        s = self.support[segment(x)]
        return (
            s["censored_rate"] <= 0.4
            and s["duration_missions"] >= 30
            and s["duration_groups"] >= 3
        )

    def format_prediction(self, x, p, duration):
        accumulated = max(0.0, -x["to_deadline_minutes"])
        out = {
            "model_version": "m02-v1",
            "domain": "synthetic_D03_v1_only",
            "regime": x["regime"],
            "phase": x["phase"],
            "probability_late": None,
            "conditional_delay_minutes": None,
            "remaining_minutes": None,
            "accumulated_delay_minutes": accumulated,
            "final_delay_minutes": None,
            "duration_interval_minutes": None,
            "final_delay_interval_minutes": None,
            "nominal_coverage": 0.8,
            "interval_condition": "late_and_quota_reached_within_observation_window",
            "status": "abstain",
            "reasons": [],
            "observed_factors": {
                k: x[k]
                for k in (
                    "phase",
                    "elapsed_minutes",
                    "deficit_units",
                    "accepted_fraction",
                    "unusable_inspected",
                    "observed_recoveries",
                )
            },
        }
        reason = self.support_reason(x)
        if reason:
            out["reasons"] = [reason]
            return out
        out["training_segment"] = self.support[segment(x)]
        if x["regime"] == "pre":
            out["probability_late"] = float(p)
            out["status"] = "probability_only"
        if not self.duration_supported(x):
            out["reasons"] = ["insufficient_uncensored_duration_support"]
            return out
        duration = max(0.0, float(duration))
        interval = self.intervals.get(x["regime"], GroupInterval(None, 0)).bounds(
            duration
        )
        out["duration_interval_minutes"] = interval
        out["status"] = "available_conditional_duration"
        if x["regime"] == "pre":
            out["conditional_delay_minutes"] = duration
            out["final_delay_minutes"] = duration
            out["final_delay_interval_minutes"] = interval
        else:
            out["remaining_minutes"] = duration
            out["final_delay_minutes"] = accumulated + duration
            out["final_delay_interval_minutes"] = (
                [accumulated + v for v in interval] if interval else None
            )
        out["reasons"] = ["duration_excludes_censored_outcomes"]
        if interval is None:
            out["reasons"].append("insufficient_interval_calibration_groups")
        return out

    def predict_many(self, rows):
        probabilities = np.full(len(rows), np.nan)
        durations = np.full(len(rows), np.nan)
        for regime in ("pre", "post"):
            idx = [i for i, r in enumerate(rows) if r["x"]["regime"] == regime]
            members = [rows[i] for i in idx]
            durations[idx] = predict_model(self.models[regime], members, regime)
            if regime == "pre" and idx:
                p = predict_model(
                    self.models["classification"], members, "classification"
                )
                logit = np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1))
                probabilities[idx] = self.calibrator.predict_proba(
                    logit.reshape(-1, 1)
                )[:, 1]
        return [
            self.format_prediction(r["x"], probabilities[i], durations[i])
            for i, r in enumerate(rows)
        ]

    def predict(self, creation, observation):
        try:
            x = rolling_features(creation, observation)
        except PredictionStopped as e:
            return {"model_version": "m02-v1", "status": "stopped", "reasons": [str(e)]}
        except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
            return {
                "model_version": "m02-v1",
                "status": "abstain",
                "reasons": ["invalid_rolling_observation"],
            }
        result = self.predict_many([{"x": x}])[0]
        result.update(
            observation_id=observation["observation_id"],
            observed_s=observation["observed_s"],
        )
        return result

    def predict_creation(self, observation):
        result = self.initial.predict(observation)
        result["initial_model_version"] = result["model_version"]
        result["model_version"] = "m02-v1"
        point = result.get("conditional_delay_minutes")
        result["interval"] = (
            self.intervals.get("initial", GroupInterval(None, 0)).bounds(point)
            if point is not None
            else None
        )
        result["nominal_coverage"] = 0.8
        result["interval_condition"] = (
            "late_and_quota_reached_within_observation_window"
        )
        if point is not None and result["interval"] is None:
            result["reasons"].append("insufficient_interval_calibration_groups")
        return result


def fit_predictor(training, calibration, choices, initial):
    if {r["split"] for r in training} != {"training"} or {
        r["split"] for r in calibration
    } != {"calibration"}:
        raise ValueError("invalid fit splits")
    if {r["group"] for r in training} & {r["group"] for r in calibration}:
        raise ValueError("group leakage")
    models = {task: fit_model(training, name, task) for task, name in choices.items()}
    cal = [r for r in calibration if included(r, "classification")]
    p = predict_model(models["classification"], cal, "classification")
    logit = np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1))
    sigmoid = LogisticRegression(C=1, random_state=1402).fit(
        logit.reshape(-1, 1),
        [r["target"]["late"] for r in cal],
        sample_weight=weights(cal),
    )
    support = {}
    for key in sorted({segment(r["x"]) for r in training}):
        members = [r for r in training if segment(r["x"]) == key]
        missions = {tuple(r["key"]): r for r in members}
        completed = [r for r in members if included(r, r["x"]["regime"])]
        support[key] = {
            "missions": len(missions),
            "groups": len({r["group"] for r in members}),
            "censored_rate": sum(
                r["target"]["quota_censored"] for r in missions.values()
            )
            / len(missions),
            "duration_missions": len({tuple(r["key"]) for r in completed}),
            "duration_groups": len({r["group"] for r in completed}),
        }
    ranges, categories = {}, {}
    for regime in ("pre", "post"):
        members = [r for r in training if r["x"]["regime"] == regime]
        keys = members[0]["x"]
        ranges[regime] = {
            k: (min(r["x"][k] for r in members), max(r["x"][k] for r in members))
            for k in keys
            if not isinstance(keys[k], str)
        }
        categories[regime] = {
            k: sorted({r["x"][k] for r in members})
            for k in keys
            if isinstance(keys[k], str)
        }
    return RollingPredictor(models, sigmoid, support, ranges, categories, {}, initial)


def calibrate_intervals(model, calibration, creations):
    predictions = model.predict_many(calibration)
    for regime in ("pre", "post"):
        errors = []
        for row, p in zip(calibration, predictions):
            if (
                not included(row, regime)
                or p["status"] != "available_conditional_duration"
            ):
                continue
            point = (
                p["conditional_delay_minutes"]
                if regime == "pre"
                else p["remaining_minutes"]
            )
            errors.append((row["group"], abs(row["target"]["target_minutes"] - point)))
        model.intervals[regime] = GroupInterval.calibrate(errors)
    errors = []
    for row in creations:
        if not row["masks"]["delay_regression"]:
            continue
        point = model.initial.predict(row["observation"])["conditional_delay_minutes"]
        if point is not None:
            errors.append((row["group"], abs(row["label"]["delay_minutes"] - point)))
    model.intervals["initial"] = GroupInterval.calibrate(errors)
    return model


def interval_metrics(rows, predictions, task):
    selected, covered, widths = [], [], []
    for row, prediction in zip(rows, predictions):
        if included(row, task) and prediction["duration_interval_minutes"] is not None:
            lower, upper = prediction["duration_interval_minutes"]
            selected.append(row)
            covered.append(lower <= row["target"]["target_minutes"] <= upper)
            widths.append(upper - lower)
    if not selected:
        return {"snapshots": 0, "missions": 0, "coverage": None, "width_minutes": None}
    w = weights(selected)
    group_covered = defaultdict(list)
    for row, c in zip(selected, covered):
        group_covered[row["group"]].append(c)
    return {
        "snapshots": len(selected),
        "missions": len({tuple(r["key"]) for r in selected}),
        "groups": len(group_covered),
        "coverage": float(np.average(covered, weights=w)),
        "width_minutes": float(np.average(widths, weights=w)),
        "sampled_group_simultaneous_coverage": float(
            np.mean([all(v) for v in group_covered.values()])
        ),
    }
