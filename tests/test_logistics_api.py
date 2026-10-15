from copy import deepcopy
from decimal import Decimal

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from src.api import logistics
from src.api.app import app
from src.api.logistics import (
    Advance,
    NewSession,
    Session,
    SessionStore,
    load_forecaster,
)
from src.logistics.core import Mission, MissionLine
from tests.test_recovery import fixture


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(logistics, "store", SessionStore())
    with TestClient(app) as c:
        yield c


def create(client, **body):
    response = client.post("/v1/sessions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def send(client, view, route, **fields):
    return client.post(
        f"/v1/sessions/{view['session_id']}/{route}",
        json={
            "command_id": f"cmd{view['revision']}",
            "expected_revision": view["revision"],
            **fields,
        },
    )


def mission(client, view, **fields):
    return send(
        client,
        view,
        "missions",
        **{
            "origin_id": "central-a",
            "destination_id": "local-a",
            "deadline_s": 86400,
            "quantities": {"food-small": 10},
            **fields,
        },
    )


def test_four_views_registry_and_lifecycle(client):
    a, b = create(client), create(client)
    assert {
        "missions",
        "depots",
        "fleet",
        "network",
        "analysis",
        "approvals",
    } <= a.keys()
    assert a["missions"] == [] and a["observed_s"] == 0
    assert len(a["fleet"]) == 10 and len(a["depots"]) == 5
    assert len(client.get("/v1/catalog").json()["items"]) == 15
    quality = client.get("/v1/model-quality").json()
    assert quality["active"] is None and quality["evaluation"]["test_consumed"]
    assert (
        client.post("/v1/sessions", json={"forecast_mode": "approved"}).status_code
        == 409
    )
    response = mission(client, a)
    assert response.status_code == 200, response.text
    view = response.json()
    m = view["missions"][0]
    assert m["lines"][0]["minimum"] == 8
    assert m["outcome"]["delay_minutes"] is None
    assert m["prediction"]["status"] == "abstain"
    assert mission(client, a).json() == view
    assert send(client, a, "advance", target_s=300).status_code == 409
    assert client.get(f"/v1/sessions/{b['session_id']}").json()["missions"] == []
    view = send(
        client,
        view,
        "cancellations",
        mission_id=m["mission_id"],
        reason="operator test",
    ).json()
    assert view["missions"][0]["outcome"]["status"] == "cancelled"
    assert view["analysis"]["cancelled"] == 1 and view["analysis"]["censored_now"] == 0
    assert client.delete(f"/v1/sessions/{a['session_id']}").status_code == 204
    assert client.get(f"/v1/sessions/{a['session_id']}").status_code == 404


@pytest.mark.parametrize(
    "fields",
    [
        {"quantities": {"unknown": 2}},
        {"quantities": {"food-small": -1}},
        {"quantities": {"food-small": True}},
        {"quantities": {"food-small": 1.5}},
        {"quantities": {"food-small": 1001}},
        {"quantities": {}},
        {"destination_id": "central-a"},
        {"origin_id": "missing"},
        {"destination_id": "local-c", "quantities": {"cold-small": 2}},
        {"deadline_s": 0},
        {"unexpected": True},
    ],
)
def test_invalid_manual_inputs_are_atomic(client, fields):
    view = create(client)
    assert mission(client, view, **fields).status_code == 422
    assert client.get(f"/v1/sessions/{view['session_id']}").json() == view


def test_chronology_and_limits(client):
    view = create(client)
    for target in (0, 3601):
        assert send(client, view, "advance", target_s=target).status_code == 422
    for _ in range(13):
        response = send(client, view, "advance", target_s=view["observed_s"] + 3600)
        assert response.status_code == 200, response.text
        view = response.json()
    assert view["missions"]
    assert all(m["start_s"] <= view["observed_s"] for m in view["missions"])
    assert "actual_s" not in str(view)
    for _ in range(7):
        create(client)
    assert client.post("/v1/sessions", json={}).status_code == 429
    assert client.post("/v1/sessions", json={"seed": 1000}).status_code == 422


def prepared():
    session = Session(NewSession(), logistics.ROOT)
    w = fixture()
    w.receive("stock", 0, "origin", {"a": 20})
    m = Mission(
        "run", "m", "origin", "dest", 0, 2500, (MissionLine("a", 10, Decimal(".9")),)
    )
    w.register("mission", 0, m)
    w.schedule("schedule", 0, "m")
    w.advance("step", 1000)
    w.observed_environment = lambda: None
    session.w = w
    return session


def test_hidden_damage_supplier_future_and_inspection():
    session = prepared()
    before = session.view()
    session.w.damage_cargo("damage", 1000, "auto-1-0", "a", 2)
    assert session.view() == before
    session.w.order_supply(
        "supply",
        1000,
        "s1",
        "origin",
        {"a": 2},
        2000,
        actual_s=4000,
        actual_quantities={"a": 1},
    )
    before = session.view()
    session.w._supplies["s1"]["actual_s"] = 5000
    session.w._supplies["s1"]["actual"] = {"a": 2}
    assert session.view() == before
    session.w.advance("inspection", 2400)
    view = session.view()
    assert view["missions"][0]["lines"][0]["accepted"] == 8
    assert view["missions"][0]["lines"][0]["unusable_inspected"] == 2
    assert not any(
        k in str(view) for k in ("hidden_bad", "cold_exposure", "selection", "actual_s")
    )
    view["missions"][0]["lines"][0]["accepted"] = 999
    assert session.view()["missions"][0]["lines"][0]["accepted"] == 8


def test_manual_recovery_and_rejected_decision(client):
    session = prepared()
    session.w.breakdown("failure", 1000, "v0", False, 86400)
    logistics.store.sessions[session.id] = session
    view = session.view()
    assert view["approvals"]["requests"]["request-1"]["status"] == "pending"
    assert (
        send(
            client, view, "decisions", request_id="missing", decision="approve"
        ).status_code
        == 422
    )
    assert logistics.store.read(session.id) == view
    response = send(
        client, view, "decisions", request_id="request-1", decision="approve"
    )
    assert response.status_code == 200, response.text
    assert response.json()["approvals"]["requests"]["request-1"]["status"] in (
        "approved",
        "in_progress",
    )
    assert "approval_due" not in str(response.json())


def test_experimental_history_deadline_and_cancellation(client):
    forecast = load_forecaster("experimental", logistics.ROOT)
    assert (
        forecast.model_sha256
        == "963a2f5d612a224e91f2f08d498036ed68cd9d9210401aac9a5d0e9cac20801f"
    )
    view = create(client, forecast_mode="experimental")
    assert "NON PROMOSSO" in view["forecast_label"]
    view = mission(client, view, deadline_s=650).json()
    view = send(client, view, "advance", target_s=2000).json()
    history = view["missions"][0]["prediction_history"]
    assert any(
        r["observed_s"] == 650 and "deadline" in r["trigger_reasons"] for r in history
    )
    assert any(
        r["observed_s"] == 1800 and "periodic" in r["trigger_reasons"] for r in history
    )
    assert all(
        r.get("probability_late") is None for r in history if r["observed_s"] >= 650
    )
    view = send(
        client,
        view,
        "cancellations",
        mission_id=view["missions"][0]["mission_id"],
        reason="test",
    ).json()
    assert view["missions"][0]["prediction"]["status"] == "stopped"


def test_missing_evidence_invariant_stop_and_cache(monkeypatch, tmp_path):
    with pytest.raises(HTTPException) as exc:
        load_forecaster("experimental", tmp_path)
    assert exc.value.status_code == 503
    store = SessionStore()
    v = store.create(NewSession())

    def broken(self, target):
        raise ValueError("conservation violation")

    monkeypatch.setattr(Session, "advance", broken)
    body = Advance(command_id="a", expected_revision=0, target_s=300)
    with pytest.raises(HTTPException) as exc:
        store.command(v["session_id"], "advance", body)
    assert exc.value.detail["field"] == "simulation"
    assert not store.read(v["session_id"])["valid"]
    with pytest.raises(HTTPException):
        store.command(v["session_id"], "advance", body)
    assert deepcopy(store.read(v["session_id"])) == store.read(v["session_id"])


def test_resource_events_trigger_forecast_without_latent_leakage():
    from src.logistics.forecast_session import ForecastSession
    from tests.test_forecast_session import RecordingModel

    session = prepared()
    session.forecast = ForecastSession(RecordingModel(), "0" * 64)
    session.forecast.register(
        {
            "simulation_id": "run",
            "mission_id": "m",
            "observed_s": 0,
            "features": {"deadline_s": 2500},
        }
    )
    before = session.resource_signature()
    session.w.damage_cargo("hidden", 1000, "auto-1-0", "a", 1)
    assert session.resource_signature() == before
    session.step(1800)
    assert any(
        "observed_resources_changed" in r.get("trigger_reasons", [])
        for r in session.forecast.records
    )
    assert session.forecast.records[-1]["observed_s"] == 1800
