import pandas as pd

from src.ml.dataset import split_features_labels
from src.ml.train_risk_model import train_risk_model

def test_split_features_labels_basic():
    """Verifica che la funzione divida correttamente X e y."""
    data = {
        "total_minutes": [30, 60, 120, 120],
        "timestep_minutes": [10, 10, 10, 20],
        "risk_label": [1, 0, 0, 1],
    }
    df = pd.DataFrame(data)

    X_train, X_test, y_train, y_test = split_features_labels(df, test_size=0.5, random_state=0)

    # Controlliamo le dimensioni
    assert len(X_train) + len(X_test) == len(df)
    assert len(y_train) + len(y_test) == len(df)

    # Verifichiamo che le colonne di X siano solo le feature numeriche
    assert list(X_train.columns) == ["total_minutes", "timestep_minutes"]

def test_train_risk_model_creates_file(tmp_path):
    """Verifica che train_risk_model crei un file modello su un dataset finto."""
    # Creiamo un piccolo dataset finto
    data = {
        "total_minutes": [30, 60, 120, 120],
        "timestep_minutes": [10, 10, 10, 20],
        "risk_label": [1, 0, 0, 1],
    }
    df = pd.DataFrame(data)

    # Percorsi temporanei
    dataset_path = tmp_path / "convoy_risk_dataset_test.csv"
    model_path = tmp_path / "risk_model_test.pkl"

    df.to_csv(dataset_path, index=False)

    # Eseguiamo il training
    train_risk_model(dataset_path=dataset_path, model_path=model_path)

    # Verifichiamo che il file modello sia stato creato
    assert model_path.exists()