
import pandas as pd

from src.ml.train_risk_model import train_risk_model


def test_train_risk_model_creates_report(tmp_path):
    """Verifica che il training crei sia il modello che il report JSON."""
    # Creiamo un piccolo dataset finto
    data = {
        "total_minutes": [30, 60, 120, 120],
        "timestep_minutes": [10, 10, 10, 20],
        "risk_label": [1, 0, 0, 1],
    }
    df = pd.DataFrame(data)

    dataset_path = tmp_path / "dataset.csv"
    df.to_csv(dataset_path, index=False)

    model_path = tmp_path / "risk_model_test.pkl"

    # Eseguiamo il training passando percorsi personalizzati
    train_risk_model(dataset_path=dataset_path, model_path=model_path)

    # Controlliamo che il modello e il report esistano
    assert model_path.exists()

    report_path = model_path.with_suffix(".report.json")
    assert report_path.exists()
