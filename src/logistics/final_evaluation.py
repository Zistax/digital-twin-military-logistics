"""Frozen M03 metrics, paired group uncertainty and explicit technical gates."""

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

POLICY = {
    "classification_ece_max": 0.05,
    "duration_mae_max_minutes": 1440.0,
    "duration_improvement_min": 0.1,
    "interval_coverage_min": 0.8,
    "interval_group_coverage_min": 0.8,
    "interval_width_max_minutes": 2880.0,
    "probability_availability_min": 0.95,
    "duration_availability_min": 0.5,
    "segment_missions_min": 100,
    "segment_groups_min": 5,
    "segment_class_min": 20,
    "segment_completed_min": 30,
    "bootstrap_repetitions": 1000,
    "bootstrap_seed": 1503,
}


def mission_weights(rows):
    counts = {}
    for row in rows:
        key = tuple(row["key"])
        counts[key] = counts.get(key, 0) + 1
    return np.array([1 / counts[tuple(r["key"])] for r in rows])


def summary(rows, probability=None, duration=None, intervals=None, baseline=None):
    result = {
        "missions": len({tuple(r["key"]) for r in rows}),
        "snapshots": len(rows),
        "groups": len({r["group"] for r in rows}),
    }
    if not rows:
        return result
    w = mission_weights(rows)
    if probability is not None:
        y, p = np.array([r["late"] for r in rows]), np.asarray(probability)
        bins = np.minimum((p * 10).astype(int), 9)
        result.update(
            brier=float(np.average((y - p) ** 2, weights=w)),
            ece=float(
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
            roc_auc=(
                float(roc_auc_score(y, p, sample_weight=w))
                if len(set(y)) == 2
                else None
            ),
            pr_auc=(
                float(average_precision_score(y, p, sample_weight=w))
                if len(set(y)) == 2
                else None
            ),
            class_missions={
                str(value): len({tuple(r["key"]) for r in rows if r["late"] == value})
                for value in (False, True)
            },
        )
        if baseline is not None:
            result["baseline_brier"] = float(
                np.average((y - np.asarray(baseline)) ** 2, weights=w)
            )
    if duration is not None:
        y, p = np.array([r["duration"] for r in rows]), np.asarray(duration)
        result.update(
            mae_minutes=float(np.average(abs(y - p), weights=w)),
            error_over_1_day=float(np.average(abs(y - p) > 1440, weights=w)),
        )
        if baseline is not None:
            b = float(np.average(abs(y - np.asarray(baseline)), weights=w))
            result["baseline_mae_minutes"] = b
            result["relative_mae_improvement"] = (
                1 - result["mae_minutes"] / b if b > 0 else None
            )
    if intervals is not None:
        bounds = np.asarray(intervals)
        y = np.array([r["duration"] for r in rows])
        covered = (bounds[:, 0] <= y) & (y <= bounds[:, 1])
        group_coverage = {
            g: bool(all(covered[i] for i, r in enumerate(rows) if r["group"] == g))
            for g in {r["group"] for r in rows}
        }
        result.update(
            coverage=float(np.average(covered, weights=w)),
            width_minutes=float(np.average(bounds[:, 1] - bounds[:, 0], weights=w)),
            group_simultaneous_coverage=float(np.mean(list(group_coverage.values()))),
            per_group_coverage=group_coverage,
        )
    return result


def sufficient(metrics, classification=False):
    if metrics["groups"] < POLICY["segment_groups_min"]:
        return False
    if classification:
        return metrics["missions"] >= POLICY["segment_missions_min"] and (
            min(metrics.get("class_missions", {}).values(), default=0)
            >= POLICY["segment_class_min"]
        )
    return metrics["missions"] >= POLICY["segment_completed_min"]


def uncertainty(rows, prediction, baseline, classification=False, intervals=None):
    """Resample paired groups; preserve each mission's original total weight."""
    groups = sorted({r["group"] for r in rows})
    w = mission_weights(rows)
    y = np.array([r["late" if classification else "duration"] for r in rows])
    p, b = np.asarray(prediction), np.asarray(baseline)
    loss = (y - p) ** 2 if classification else abs(y - p)
    reference = (y - b) ** 2 if classification else abs(y - b)
    rng = np.random.default_rng(POLICY["bootstrap_seed"])
    draws = rng.integers(
        0, len(groups), size=(POLICY["bootstrap_repetitions"], len(groups))
    )
    idx = {
        g: np.array([i for i, r in enumerate(rows) if r["group"] == g]) for g in groups
    }
    total = np.array([sum(w[idx[g]]) for g in groups])

    def interval(values):
        sums = np.array([sum(values[idx[g]] * w[idx[g]]) for g in groups])
        sampled = np.sum(sums[draws], axis=1) / np.sum(total[draws], axis=1)
        return [float(v) for v in np.quantile(sampled, [0.025, 0.975])]

    result = {
        "paired_difference_95": interval(loss - reference),
        "metric_95": interval(loss),
    }
    if intervals is not None:
        bounds = np.asarray(intervals)
        result["coverage_95"] = interval(
            ((bounds[:, 0] <= y) & (y <= bounds[:, 1])).astype(float)
        )
        result["width_minutes_95"] = interval(bounds[:, 1] - bounds[:, 0])
    return result


def performance_checks(metrics, classification=False, require_ci=False):
    required = "brier" if classification else "coverage"
    if required not in metrics:
        return {"metrics_available": False}
    if classification:
        checks = {
            "brier_beats_prevalence": metrics["brier"] < metrics["baseline_brier"],
            "ece": metrics["ece"] <= POLICY["classification_ece_max"],
        }
    else:
        improvement = metrics.get("relative_mae_improvement")
        checks = {
            "duration_mae": metrics["mae_minutes"]
            <= POLICY["duration_mae_max_minutes"],
            "duration_improvement": improvement is not None
            and improvement >= POLICY["duration_improvement_min"],
            "interval_coverage": metrics["coverage"] >= POLICY["interval_coverage_min"],
            "interval_width": metrics["width_minutes"]
            <= POLICY["interval_width_max_minutes"],
            "interval_group_coverage": metrics["group_simultaneous_coverage"]
            >= POLICY["interval_group_coverage_min"],
        }
    if require_ci:
        checks["paired_improvement_ci"] = metrics["paired_difference_95"][1] < 0
    return checks


def gates(channels, segments, availability, integrity=True):
    checks = {"integrity": bool(integrity), "frequency_validated_at_30_minutes": False}
    for name, m in channels.items():
        classification = name.endswith("classification")
        checks.update(
            {
                name + "|" + k: v
                for k, v in performance_checks(m, classification, True).items()
            }
        )
        checks[name + "|sufficient"] = sufficient(m, classification)
    for name, m in segments.items():
        if not m["required"]:
            continue
        classification = m["channel"].endswith("classification")
        enough = sufficient(m, classification)
        checks[name + "|sufficient"] = enough
        if enough:
            checks.update(
                {
                    name + "|" + k: v
                    for k, v in performance_checks(m, classification).items()
                }
            )
    for stage, m in availability.items():
        checks[stage + "|duration_availability"] = (
            m["duration"] >= POLICY["duration_availability_min"]
        )
        if stage != "post":
            checks[stage + "|probability_availability"] = (
                m["probability"] >= POLICY["probability_availability_min"]
            )
    return {
        "eligible": all(checks.values()),
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "manual_approval_required": True,
        "promoted": False,
    }
