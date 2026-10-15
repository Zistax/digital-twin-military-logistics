from copy import deepcopy
from decimal import Decimal

import pytest

from src.logistics.core import Mission, MissionLine
from src.logistics.forecast_session import ForecastSession
from tests.test_recovery import fixture


class RecordingModel:
    def predict_creation(self, creation):
        return {"model_version": "m02-v1", "status": "probability_only"}

    def predict(self, creation, observation):
        return {"model_version": "m02-v1", "status": "probability_only"}


def setup(deadline=650):
    w = fixture()
    w.receive("stock", 0, "origin", {"a": 20})
    mission = Mission(
        "run",
        "m",
        "origin",
        "dest",
        0,
        deadline,
        (MissionLine("a", 10, Decimal(".9")),),
    )
    creation = {
        "simulation_id": "run",
        "mission_id": "m",
        "observed_s": 0,
        "features": {"deadline_s": deadline},
    }
    w.register("mission", 0, mission)
    w.schedule("schedule", 0, "m")
    session = ForecastSession(RecordingModel(), "0" * 64)
    session.register(creation)
    return w, session, creation


def test_live_exact_deadline_periodic_events_and_stop():
    w, session, _ = setup()
    session.advance_to(w, 2500)
    deadlines = [
        r for r in session.records if "deadline" in r.get("trigger_reasons", [])
    ]
    assert [r["observed_s"] for r in deadlines] == [650]
    assert any(
        r["observed_s"] == 1800 and "periodic" in r.get("trigger_reasons", [])
        for r in session.records
    )
    assert any(
        r["observed_s"] == 600
        and "observable_state_changed" in r.get("trigger_reasons", [])
        for r in session.records
    )
    assert session.records[-1]["status"] == "stopped"
    assert session.records[-1]["reasons"] == ["quota_reached"]
    n = len(session.records)
    session.advance_to(w, 3000)
    assert len(session.records) == n
    assert all(r["model_sha256"] == "0" * 64 for r in session.records)


def test_same_clock_upserts_after_observable_batch():
    w, session, creation = setup()
    session.advance_to(w, 650)
    n = len(session.records)
    session.flush(w, ["route_changed", "availability_changed"])
    assert len(session.records) == n
    record = session.records[-1]
    assert "deadline" in record["trigger_reasons"]
    assert "route_changed" in record["trigger_reasons"]
    assert record["snapshot"]["observed_s"] == 650
    assert record["creation_snapshot"] == creation
    assert session.register(creation) is None
    changed = deepcopy(creation)
    changed["features"]["deadline_s"] = 700
    with pytest.raises(ValueError, match="conflicting"):
        session.register(changed)


def test_cancellation_stops_and_records_are_detached():
    w, session, _ = setup()
    first = session.flush(w)
    first[0]["snapshot"]["features"]["lines"][0]["reserved"] = 999
    assert session.records[-1]["snapshot"]["features"]["lines"][0]["reserved"] != 999
    w.cancel("cancel", 0, "m")
    session.flush(w)
    assert session.records[-1]["reasons"] == ["cancelled"]


def test_session_input_guards_and_required_registration():
    with pytest.raises(ValueError):
        ForecastSession(RecordingModel(), "0" * 64, interval_s=0)
    with pytest.raises(ValueError):
        ForecastSession(RecordingModel(), "wrong")
    w, session, _ = setup()
    session.advance_to(w, 100)
    with pytest.raises(ValueError):
        session.advance_to(w, 99)
    session.register(
        {
            "simulation_id": "run",
            "mission_id": "missing",
            "observed_s": 100,
            "features": {"deadline_s": 1000},
        }
    )
    with pytest.raises(ValueError, match="register mission"):
        session.flush(w)
