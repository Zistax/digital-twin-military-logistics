from __future__ import annotations

from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd


def load_risk_model(model_path: str | Path = "models/risk_model.pkl"):
    """Carica il modello di rischio da file.

    Lancia FileNotFoundError se il file non esiste.
    """
    model_path = Path(model_path)

    if not model_path.exists():
        raise FileNotFoundError(f"File modello non trovato: {model_path}")

    model = joblib.load(model_path)
    return model


def prepare_convoy_features(
    total_minutes: int,
    timestep_minutes: int,
    n_convoys: int,
) -> pd.DataFrame:
    """Crea un DataFrame di feature per n_convoys convogli.

    In questa versione semplificata:
    - tutti i convogli hanno le stesse feature (total_minutes, timestep_minutes)
    - la differenza tra convogli non è ancora modellata (sarà migliorato in fasi successive)
    """
    if n_convoys <= 0:
        raise ValueError("n_convoys deve essere > 0")

    data = {
        "convoy_id": list(range(1, n_convoys + 1)),
        "total_minutes": [total_minutes] * n_convoys,
        "timestep_minutes": [timestep_minutes] * n_convoys,
    }

    df = pd.DataFrame(data)
    return df


def predict_convoy_risk_proba(
    model,
    total_minutes: int,
    timestep_minutes: int,
    n_convoys: int,
) -> pd.DataFrame:
    """Restituisce un DataFrame con la probabilità di rischio per ogni convoglio.

    Ritorna un DataFrame con colonne:
    - convoy_id
    - risk_proba (probabilità che risk_label == 1)
    """
    df_features = prepare_convoy_features(total_minutes, timestep_minutes, n_convoys)

    # Le colonne di feature devono corrispondere a quelle usate in training
    X = df_features[["total_minutes", "timestep_minutes"]].copy()

    # predict_proba restituisce un array shape (n_samples, 2)
    # colonna 0 = prob classe 0, colonna 1 = prob classe 1
    proba: np.ndarray = model.predict_proba(X)  # type: ignore[attr-defined]

    # Probabilità della classe "1" (convoglio a rischio)
    risk_proba = proba[:, 1]

    df_result = pd.DataFrame(
        {
            "convoy_id": df_features["convoy_id"],
            "risk_proba": risk_proba,
        }
    )

    return df_result