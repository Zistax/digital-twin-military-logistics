from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


def test_predict_risk_basic(monkeypatch):
    """Test di base per /predict_risk con valori standard.

    Usiamo monkeypatch per evitare di caricare il vero modello da disco,
    sostituendo load_risk_model con una versione fittizia se necessario.
    """

    class DummyModel:
        def predict_proba(self, X):
            # Prob classe 0 = 0.8, classe 1 = 0.2
            import numpy as np

            n_samples = len(X)
            return np.tile([0.8, 0.2], (n_samples, 1))

    def dummy_load_risk_model(path):
        return DummyModel()

    def dummy_predict_convoy_risk_proba(model, total_minutes, timestep_minutes, n_convoys):
        import pandas as pd

        return pd.DataFrame(
            {
                "convoy_id": list(range(1, n_convoys + 1)),
                "risk_proba": [0.2] * n_convoys,
            }
        )

    # Sostituiamo temporaneamente le funzioni reali con le versioni dummy
    monkeypatch.setattr("src.api.app.load_risk_model", dummy_load_risk_model)
    monkeypatch.setattr("src.api.app.predict_convoy_risk_proba", dummy_predict_convoy_risk_proba)

    payload = {
        "total_minutes": 120,
        "timestep_minutes": 10,
        "n_convoys": 3,
    }

    response = client.post("/predict_risk", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_minutes"] == 120
    assert data["timestep_minutes"] == 10
    assert data["n_convoys"] == 3

    results = data["results"]
    assert len(results) == 3
    for item in results:
        assert "convoy_id" in item
        assert "risk_proba" in item

    data = response.json()

    assert "risk_threshold_used" in data
    results = data["results"]
    assert len(results) == 3

    for item in results:
        assert "convoy_id" in item
        assert "risk_proba" in item
        assert "is_high_risk" in item

def test_simulate_basic():
    """Verifica che l'endpoint /simulate risponda 200 e contenga i campi principali."""
    payload = {
        "schema_version": "1.0",
        "total_minutes": 60,
        "timestep_minutes": 10,
        "n_convoys": 3,
        "depot_capacity": 2,
        "simulation_name": "test_sim",
    }

    response = client.post("/simulate", json=payload)
    assert response.status_code == 200

    data = response.json()

    # Controlliamo alcuni campi chiave
    assert data["schema_version"] == "1.0"
    assert data["simulation_name"] == "test_sim"
    assert data["total_minutes"] == 60
    assert data["timestep_minutes"] == 10
    assert data["n_convoys"] == 3

    assert "kpi" in data
    kpi = data["kpi"]
    assert "n_convoys" in kpi
    assert "n_completed_convoys" in kpi
    assert "n_not_completed_convoys" in kpi