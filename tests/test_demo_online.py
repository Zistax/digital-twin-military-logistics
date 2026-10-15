"""R02 boundaries: ownership, restart/retry, expiry, quotas and worker isolation."""

from dataclasses import replace
import json
import sqlite3
import subprocess

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from src.api.demo_app import create_demo_app
from src.api.demo_store import DemoStore
from src.api.demo_worker import replay
from src.api.logistics import Advance, NewMission, NewSession

SECRET = "test-administrator-key-32-characters-minimum"


@pytest.fixture
def app(tmp_path, monkeypatch):
    app = create_demo_app(tmp_path / "demo.db", SECRET, "http://testserver")
    # Most boundary tests use the real engine in process; subprocess has its own test.
    monkeypatch.setattr(
        app.state.store,
        "simulate",
        lambda sid, config, journal: replay(
            {"sid": sid, "config": config, "journal": journal}
        ),
    )
    return app


def visitor(client):
    response = client.post("/demo/access")
    assert response.status_code == 201
    return {"Authorization": "Bearer " + response.json()["token"]}


def create(client, headers, **fields):
    response = client.post("/v1/sessions", headers=headers, json=fields)
    assert response.status_code == 201, response.text
    return response.json()


def test_public_private_and_removed_endpoints(app):
    with TestClient(app) as c:
        for path in (
            "/",
            "/assets/demo.js",
            "/assets/demo.css",
            "/health",
            "/public/examples",
            "/public/policy",
            "/v1/catalog",
            "/v1/model-quality",
        ):
            response = c.get(path)
            assert response.status_code == 200, path
            assert response.headers["cache-control"] == "no-store"
            assert (
                "frame-ancestors 'none'" in response.headers["content-security-policy"]
            )
        assert len(c.get("/public/examples").json()["runs"]) == 3
        assert c.post("/v1/sessions", json={}).status_code == 401
        assert c.get("/admin/status").status_code == 401
        assert c.get("/admin/status", headers=visitor(c)).status_code == 403
        for path in (
            "/simulate",
            "/predict",
            "/train",
            "/docs",
            "/openapi.json",
            "/assets/secret",
        ):
            assert c.get(path).status_code == 404
        assert c.get("/health", headers={"Host": "evil.example"}).status_code == 400
        assert (
            c.post(
                "/demo/access", headers={"Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        assert c.post("/v1/sessions", content=b"x" * 8193).status_code == 413


def test_ownership_revoke_and_admin(app):
    with TestClient(app) as c:
        a, b = visitor(c), visitor(c)
        first, second = create(c, a), create(c, b)
        sid = first["session_id"]
        assert sid != second["session_id"]
        for method in ("GET", "DELETE"):
            assert (
                c.request(method, f"/v1/sessions/{sid}", headers=b).status_code == 404
            )
        response = c.post(
            f"/v1/sessions/{sid}/advance",
            headers=b,
            json={"command_id": "a", "expected_revision": 0, "target_s": 300},
        )
        assert response.status_code == 404
        assert c.post("/v1/sessions", headers=a, json={}).status_code == 409
        admin = {"Authorization": "Bearer " + SECRET}
        assert c.get("/admin/status", headers=admin).json()["sessions"] == 2
        assert c.post("/admin/cleanup", headers=admin).status_code == 200
        assert c.delete("/demo/access", headers=a).status_code == 204
        assert c.get(f"/v1/sessions/{sid}", headers=a).status_code == 401
        assert (
            c.get(f"/v1/sessions/{second['session_id']}", headers=b).status_code == 200
        )


def test_restart_durable_retry_and_stale_revision(app, monkeypatch):
    store = app.state.store
    token = store.access()["token"]
    view = store.create(token, NewSession())
    sid = view["session_id"]
    body = NewMission(
        command_id="mission",
        expected_revision=0,
        origin_id="central-a",
        destination_id="local-a",
        quantities={"food-small": 10},
        deadline_s=3600,
    )
    created = store.command(token, sid, "mission", body)
    assert created["revision"] == 1
    reopened = DemoStore(store.path, SECRET)
    monkeypatch.setattr(reopened, "simulate", store.simulate)
    assert reopened.read(token, sid) == created
    assert reopened.command(token, sid, "mission", body) == created
    with pytest.raises(HTTPException) as conflict:
        reopened.command(
            token, sid, "mission", body.model_copy(update={"deadline_s": 1800})
        )
    assert conflict.value.status_code == 409
    with pytest.raises(HTTPException) as stale:
        reopened.command(
            token,
            sid,
            "advance",
            Advance(command_id="advance", expected_revision=0, target_s=300),
        )
    assert stale.value.status_code == 409
    advanced = reopened.command(
        token,
        sid,
        "advance",
        Advance(command_id="advance", expected_revision=1, target_s=300),
    )
    assert advanced["observed_s"] == 300
    assert advanced["missions"][0]["mission_id"] == created["missions"][0]["mission_id"]
    assert reopened.command(token, sid, "mission", body) == created
    assert reopened.read(token, sid) == advanced


def test_expiry_purges_journal_and_lease(app):
    store = app.state.store
    token = store.access()["token"]
    view = store.create(token, NewSession())
    store.command(
        token,
        view["session_id"],
        "advance",
        Advance(command_id="a", expected_revision=0, target_s=300),
    )
    store.clock = lambda: 10**12
    with pytest.raises(HTTPException) as expired:
        store.read(token, view["session_id"])
    assert expired.value.status_code == 401
    assert store.maintenance()["sessions"] == 0
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT count(*) FROM commands").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM leases").fetchone()[0] == 0


@pytest.mark.parametrize(
    "fields",
    [
        {"seed": 1},
        {"profile": "pressure"},
        {"forecast_mode": "approved"},
        {"unknown": True},
    ],
)
def test_presets_and_strict_inputs(app, fields):
    with TestClient(app) as c:
        assert (
            c.post("/v1/sessions", headers=visitor(c), json=fields).status_code == 422
        )


def test_quotas_and_atomic_failure(app):
    store = app.state.store
    store.policy = replace(
        store.policy, capacity=1, max_commands=1, max_manual_missions=0
    )
    token, other = store.access()["token"], store.access()["token"]
    view = store.create(token, NewSession())
    sid = view["session_id"]
    with pytest.raises(HTTPException) as full:
        store.create(other, NewSession())
    assert full.value.status_code == 429
    with pytest.raises(HTTPException) as horizon:
        store.command(
            token,
            sid,
            "advance",
            Advance(command_id="bad", expected_revision=0, target_s=301),
        )
    assert horizon.value.status_code == 422
    assert store.read(token, sid) == view
    with pytest.raises(HTTPException) as manual:
        store.command(
            token,
            sid,
            "mission",
            NewMission(
                command_id="m",
                expected_revision=0,
                origin_id="central-a",
                destination_id="local-a",
                quantities={"food-small": 1},
                deadline_s=500,
            ),
        )
    assert manual.value.status_code == 429
    cmd = Advance(command_id="good", expected_revision=0, target_s=300)
    result = store.command(token, sid, "advance", cmd)
    assert store.command(token, sid, "advance", cmd) == result
    with pytest.raises(HTTPException) as commands:
        store.command(
            token,
            sid,
            "advance",
            Advance(command_id="next", expected_revision=1, target_s=600),
        )
    assert commands.value.status_code == 429
    store.delete(token, sid)
    assert store.create(other, NewSession())["revision"] == 0


def test_rate_limits_and_minute_reset(app):
    store = app.state.store
    store.policy = replace(
        store.policy, access_per_minute=1, requests_per_minute=3, global_per_minute=4
    )
    store.clock = lambda: 120
    store.throttle("client", True)
    with pytest.raises(HTTPException) as limited:
        store.throttle("client", True)
    assert limited.value.status_code == 429
    store.clock = lambda: 180
    store.throttle("client", True)
    with TestClient(app) as c:
        c.post("/demo/access")
        response = c.post("/demo/access")
        assert response.status_code == 429
        assert response.headers["retry-after"] == "60"
    with sqlite3.connect(store.path) as db:
        assert "client" not in json.dumps(
            db.execute("SELECT key FROM rates").fetchall()
        )


def test_hard_worker_timeout_kills_and_leaves_state_unchanged(app, monkeypatch):
    store = app.state.store
    token = store.access()["token"]
    view = store.create(token, NewSession())
    original = DemoStore.simulate.__get__(store)

    class Slow:
        killed = False

        def communicate(self, *args, **kwargs):
            if not self.killed:
                raise subprocess.TimeoutExpired("worker", 20)
            return "", ""

        def kill(self):
            self.killed = True

    child = Slow()
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: child)
    monkeypatch.setattr(store, "simulate", original)
    with pytest.raises(HTTPException) as timeout:
        store.command(
            token,
            view["session_id"],
            "advance",
            Advance(command_id="a", expected_revision=0, target_s=300),
        )
    assert timeout.value.status_code == 503 and child.killed
    assert store.read(token, view["session_id"]) == view
    assert store.busy.acquire(blocking=False)
    store.busy.release()


def test_real_disposable_worker_replays_without_test_path(tmp_path):
    store = DemoStore(tmp_path / "demo.db", SECRET)
    token = store.access()["token"]
    view = store.create(token, NewSession(forecast_mode="experimental"))
    sid = view["session_id"]
    body = NewMission(
        command_id="m",
        expected_revision=0,
        origin_id="central-a",
        destination_id="local-a",
        quantities={"food-small": 10},
        deadline_s=600,
    )
    created = store.command(token, sid, "mission", body)
    advanced = store.command(
        token,
        sid,
        "advance",
        Advance(command_id="a", expected_revision=1, target_s=300),
    )
    assert advanced["revision"] == 2 and advanced["observed_s"] == 300
    assert advanced["missions"][0]["prediction_history"]
    assert DemoStore(tmp_path / "demo.db", SECRET).read(token, sid) == advanced
    assert store.command(token, sid, "mission", body) == created


def test_configuration_and_release_fingerprint(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="secret"):
        DemoStore(tmp_path / "short.db", "short")
    with pytest.raises(ValueError, match="HTTPS"):
        create_demo_app(tmp_path / "x.db", SECRET, "http://demo.example")
    with pytest.raises(ValueError, match="origin"):
        create_demo_app(tmp_path / "x.db", SECRET, "https://demo.example/path")
    store = DemoStore(tmp_path / "demo.db", SECRET)
    monkeypatch.setattr(
        store,
        "simulate",
        lambda sid, c, j: replay({"sid": sid, "config": c, "journal": j}),
    )
    store.create(store.access()["token"], NewSession())
    monkeypatch.setattr("src.api.demo_store.fingerprint", lambda root: "changed")
    with pytest.raises(ValueError, match="release changed"):
        DemoStore(store.path, SECRET)


def test_revocation_does_not_consume_token_issuance_budget(app):
    store = app.state.store
    store.policy = replace(store.policy, access_per_minute=1)
    with TestClient(app) as client:
        headers = visitor(client)
        view = create(client, headers)
        response = client.delete("/demo/access", headers=headers)
        assert response.status_code == 204, response.text
        assert (
            client.get(
                f"/v1/sessions/{view['session_id']}", headers=headers
            ).status_code
            == 401
        )
        assert client.post("/demo/access").status_code == 429
