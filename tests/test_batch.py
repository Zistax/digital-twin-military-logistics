from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json

import pytest

from src.logistics.batch import (
    audit_record,
    digest,
    execute_run,
    make_plan,
    run_batch,
    summarize,
    validate_plan,
)
from src.logistics.experiments import run_experiment
from tests.test_recovery import fixture
from tests.test_estimates import request


def small_run(config, **kwargs):
    w = fixture()
    w.simulation_id = f"scenario-{config.seed}-{config.profile}"
    w.receive("initial", 0, "origin", {"a": 20})
    return run_experiment(config, warehouse=w, requests=[request()], **kwargs)


def resign(plan):
    plan["plan_sha256"] = digest({k: v for k, v in plan.items() if k != "plan_sha256"})


def test_frozen_split_is_outcome_independent_and_exact():
    plan = make_plan()
    validate_plan(plan)
    assert len(plan["runs"]) == 90
    assert make_plan()["groups"] == plan["groups"]
    memberships = {row["seed"]: row["split"] for row in plan["runs"]}
    assert len(memberships) == 30
    assert not set(memberships) & {0, 1, 2, 3}


@pytest.mark.parametrize(
    "mutation",
    ["hash", "group", "seed", "horizon", "run", "count", "identity", "version"],
)
def test_leakage_or_plan_mutation_is_rejected(mutation):
    plan = make_plan()
    if mutation == "hash":
        plan["assignment"] = "changed"
    elif mutation == "group":
        plan["runs"][0]["split"] = "test"
    elif mutation == "seed":
        plan["groups"][0]["seed"] = 0
    elif mutation == "horizon":
        plan["extension_days"] = 0
    elif mutation == "run":
        plan["runs"].pop()
    elif mutation == "count":
        plan["groups"][0]["split"] = "test"
    elif mutation == "identity":
        plan["runs"][0]["simulation_id"] = "other"
    else:
        plan["plan_version"] = 2
    if mutation != "hash":
        resign(plan)
    with pytest.raises(ValueError):
        validate_plan(plan)


def test_full_batch_orchestration_and_resume_verify_real_small_bundles(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("src.logistics.batch.ProcessPoolExecutor", ThreadPoolExecutor)
    monkeypatch.setattr("src.logistics.batch.run_experiment", small_run)
    root = tmp_path / "batch"
    assert run_batch(root, workers=2)
    manifest = json.loads((root / "split_manifest.json").read_text())
    assert {k: len(v) for k, v in manifest["sets"].items()} == {
        "training": 54,
        "calibration": 18,
        "test": 18,
    }
    before = sorted((root / "records").glob("*.json"))
    assert len(before) == 90
    assert run_batch(root, workers=2)
    assert sorted((root / "records").glob("*.json")) == before
    plan = json.loads((root / "plan.json").read_text())
    record = json.loads(before[0].read_text())
    row = next(r for r in plan["runs"] if r["simulation_id"] == record["simulation_id"])
    broken = deepcopy(record)
    broken["manifest_sha256"] = "changed"
    with pytest.raises(ValueError):
        audit_record((str(root), row, plan, broken))
    records = sum(manifest["sets"].values(), [])
    with pytest.raises(ValueError):
        summarize(plan, records[:-1])
    records[0]["kpi"]["missions"] += 1
    with pytest.raises(ValueError):
        summarize(plan, records)


def test_failed_attempt_is_preserved_with_diagnosis(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("intentional invalid run")

    monkeypatch.setattr("src.logistics.batch.run_experiment", fail)
    (tmp_path / "records").mkdir()
    plan = make_plan()
    row = plan["runs"][0]
    record = execute_run((str(tmp_path), row, plan, 1))
    assert record["valid"] is False
    assert record["error"] == "intentional invalid run"
    saved = json.loads(next((tmp_path / "records").glob("*.json")).read_text())
    assert saved == record


def test_batch_sources_cannot_change_after_freeze(tmp_path, monkeypatch):
    monkeypatch.setattr("src.logistics.batch.ProcessPoolExecutor", ThreadPoolExecutor)
    monkeypatch.setattr("src.logistics.batch.run_experiment", small_run)
    plan = make_plan()
    plan["source_sha256"]["core.py"] = "other"
    resign(plan)
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="changed simulator"):
        run_batch(tmp_path)
    with pytest.raises(ValueError):
        run_batch(tmp_path, workers=True)
