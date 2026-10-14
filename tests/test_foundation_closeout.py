from copy import deepcopy
import json

import pytest

from src.logistics.context import validate_context_journal
from src.logistics.journal import Journal
from src.logistics.pilot import run_pilot
from src.logistics.experiments import run_experiment
from src.logistics.training_masks import creation_masks, rolling_masks
from tests.test_dataset import run
from tests.test_recovery import fixture
from tests.test_estimates import request


@pytest.mark.parametrize(
    "change",
    ["stock", "available", "fleet", "cursor", "supplies", "queue", "environment"],
)
def test_context_cannot_disagree_with_exact_journal_state(change):
    result = run()
    rows = deepcopy(result["planning_contexts"])
    context = rows[0]["context"]
    if change in ("stock", "available"):
        context["depots"]["origin"][change]["a"] += 1
    elif change == "fleet":
        context["fleet"]["v0"]["busy"] = True
    elif change == "cursor":
        rows[0]["journal_event_id"] = "state:999999"
    elif change == "supplies":
        context["supplies"]["invented"] = {}
    elif change == "queue":
        context["depots"]["origin"]["queue_size"] += 1
    else:
        context["environment"] = {"observed_s": 0}
    with pytest.raises(ValueError):
        validate_context_journal(rows, result["operational_events"])


def test_rejected_command_rolls_back_journal_and_physical_state():
    w = fixture()
    w._journal = Journal()
    w._journal.capture(w, 0)
    before = w.snapshot()
    records = w._journal.records
    with pytest.raises(ValueError):
        w.receive("bad", 10, "origin", {"a": 10**12})
    assert w.snapshot() == before
    assert w._journal.records == records
    w.receive("good", 0, "origin", {"a": 20})
    captured = w._journal.records
    w.receive("good", 0, "origin", {"a": 20})
    assert w._journal.records == captured


@pytest.mark.parametrize("fail_pressure", [False, True])
def test_pilot_checkpoints_verified_bundles_and_keeps_failures(
    tmp_path, monkeypatch, fail_pressure
):
    def small_run(config, **kwargs):
        if fail_pressure and config.profile == "pressure":
            raise RuntimeError("injected run failure")
        w = fixture()
        w.receive("stock", 0, "origin", {"a": 20})
        return run_experiment(config, warehouse=w, requests=[request()], **kwargs)

    monkeypatch.setattr("src.logistics.pilot.run_experiment", small_run)
    report = run_pilot(tmp_path / "pilot", generation_days=1, extension_days=0)
    assert report["all_valid"] is (not fail_pressure)
    assert len(report["runs"]) == 3
    saved = json.loads((tmp_path / "pilot" / "pilot.json").read_text())
    assert saved == report
    assert report["runs"][2]["valid"]
    if fail_pressure:
        assert report["runs"][1]["error_type"] == "RuntimeError"


def test_training_masks_preserve_censoring_and_skip_post_deadline_classifier():
    label = {
        "eligible": True,
        "status": "incomplete",
        "late": True,
        "delay_minutes": None,
        "quota_censored": True,
    }
    assert creation_masks(label) == {
        "classification": True,
        "delay_regression": False,
        "censored": True,
    }
    label.update(status="cancelled", eligible=False)
    assert not any(creation_masks(label).values())
    target = {
        "eligible": True,
        "target_kind": "remaining_after_deadline",
        "late": True,
        "target_minutes": 10,
        "quota_censored": False,
    }
    assert rolling_masks(target) == {
        "classification": False,
        "duration_regression": True,
        "censored": False,
    }


def test_observable_environment_context_uses_the_persisted_key_format():
    from src.logistics.scenarios import ScenarioConfig
    from src.logistics.bundles import validate_bundle_tables
    from src.logistics.dataset import export_creation_dataset
    from tempfile import TemporaryDirectory
    from pathlib import Path

    result = run_experiment(ScenarioConfig(seed=3, generation_days=1, extension_days=0))
    validate_context_journal(result["planning_contexts"], result["operational_events"])
    with TemporaryDirectory() as directory:
        root = Path(directory) / "bundle"
        manifest = export_creation_dataset(result, root)
        tables = {
            name: [json.loads(line) for line in (root / name).read_text().splitlines()]
            for name in manifest["files"]
        }
        validate_bundle_tables(manifest, tables)
