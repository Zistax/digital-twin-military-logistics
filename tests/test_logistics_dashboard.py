"""Exercise the rendered dashboard against the real FastAPI backend in process."""

from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
import requests
from streamlit.testing.v1 import AppTest

from src.api import logistics
from src.api.app import app
from src.api.logistics import SessionStore


def test_four_tabs_mission_advance_refresh_and_close(monkeypatch):
    monkeypatch.setattr(logistics, "store", SessionStore())
    client = TestClient(app)

    def request(method, url, json=None, timeout=None):
        response = client.request(method, urlsplit(url).path, json=json)
        response.ok = response.is_success
        return response

    monkeypatch.setattr(requests, "request", request)
    path = Path(__file__).resolve().parents[1] / "src/ui/dashboard.py"
    ui = AppTest.from_file(str(path), default_timeout=30).run()
    assert not ui.exception
    assert "crea una sessione" in ui.info[0].value
    next(b for b in ui.button if b.label == "Crea sessione").click().run()
    assert not ui.exception
    assert [tab.label for tab in ui.tabs] == [
        "Missioni e previsioni",
        "Depositi e scorte",
        "Flotta e rete",
        "Analisi e qualità modello",
    ]
    next(b for b in ui.button if b.label == "Registra missione").click().run()
    assert not ui.exception
    assert ui.session_state["view"]["missions"][0]["lines"][0]["minimum"] == 8
    next(b for b in ui.button if b.label == "Avanza di un'ora").click().run()
    assert not ui.exception
    assert ui.session_state["view"]["observed_s"] == 3600
    next(b for b in ui.button if b.label == "Aggiorna dati").click().run()
    assert not ui.exception
    next(b for b in ui.button if b.label == "Chiudi sessione").click().run()
    assert not ui.exception
    assert "view" not in ui.session_state
