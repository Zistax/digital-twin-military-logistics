import numpy as np
import pytest

from logistics import final_evaluation as ev


def rows():
    return [
        {"key": ["s", str(i)], "group": f"g{i}", "late": bool(i % 2), "duration": 0.0}
        for i in range(6)
    ]


def test_equal_mission_weight_ignores_snapshot_multiplicity():
    data = [rows()[0]] * 20 + [rows()[1]]
    w = ev.mission_weights(data)
    assert sum(w[:20]) == pytest.approx(1)
    assert w[-1] == 1
    m = ev.summary(data, probability=[1.0] * 21)
    assert m["brier"] == pytest.approx(0.5)
    assert m["missions"] == 2
    assert ev.summary([])["snapshots"] == 0


def test_paired_group_bootstrap_and_interval_uncertainty():
    data = rows()
    m = ev.uncertainty(data, [1.0] * 6, [2.0] * 6, False, [[0, 2]] * 6)
    assert m["paired_difference_95"] == [-1, -1]
    assert m["metric_95"] == [1, 1]
    assert m["coverage_95"] == [1, 1]
    assert m["width_minutes_95"] == [2, 2]
    p = np.array([r["late"] for r in data], dtype=float)
    c = ev.uncertainty(data, p, 1 - p, True)
    assert c["paired_difference_95"] == [-1, -1]


def test_metrics_and_small_segments_are_explicit():
    data = rows()
    p = np.array([r["late"] for r in data], dtype=float)
    c = ev.summary(data, probability=p, baseline=1 - p)
    assert c["roc_auc"] == 1 and c["brier"] == 0 and c["baseline_brier"] == 1
    assert not ev.sufficient(c, True)
    c.update(missions=100, class_missions={"False": 50, "True": 50})
    assert ev.sufficient(c, True)
    c["groups"] = 2
    assert not ev.sufficient(c, True)
    d = ev.summary(data, duration=[1.0] * 6, intervals=[[0, 2]] * 6, baseline=[2.0] * 6)
    assert d["relative_mae_improvement"] == 0.5 and d["coverage"] == 1
    d.update(missions=30)
    assert ev.sufficient(d)
    assert ev.summary([data[0]], probability=[0.5])["roc_auc"] is None


def test_gate_reports_failure_and_never_automatically_promotes():
    c = {
        "missions": 120,
        "groups": 6,
        "class_missions": {"False": 60, "True": 60},
        "brier": 0.1,
        "baseline_brier": 0.2,
        "ece": 0.01,
        "paired_difference_95": [-0.2, -0.1],
    }
    d = {
        "missions": 60,
        "groups": 6,
        "mae_minutes": 100,
        "relative_mae_improvement": 0.5,
        "coverage": 1.0,
        "width_minutes": 200,
        "group_simultaneous_coverage": 1.0,
        "paired_difference_95": [-100, -100],
    }
    available = {
        name: {"probability": 1.0, "duration": 1.0}
        for name in ("initial", "pre", "post")
    }
    g = ev.gates({"initial_classification": c, "initial_duration": d}, {}, available)
    assert g["failed"] == ["frequency_validated_at_30_minutes"]
    assert not g["eligible"] and not g["promoted"] and g["manual_approval_required"]
    d["width_minutes"] = 20000
    segment = dict(d, required=True, channel="initial_duration", missions=1)
    g = ev.gates({"initial_duration": d}, {"small": segment}, available, False)
    assert "initial_duration|interval_width" in g["failed"]
    assert "small|sufficient" in g["failed"]
    assert ev.performance_checks({"missions": 0}, False) == {"metrics_available": False}
