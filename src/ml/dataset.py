from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd
from sklearn.model_selection import train_test_split


def load_convoy_risk_dataset(
    csv_path: str | Path = "data/processed/convoy_risk_dataset.csv",
) -> pd.DataFrame:
    """Carica il dataset dei convogli da un file CSV."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"File dataset non trovato: {csv_path}")

    df = pd.read_csv(csv_path)
    return df


def split_features_labels(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    label_col: str = "risk_label",
    test_size: float = 0.3,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Divide il dataset in train/test per un problema di classificazione binaria."""
    if label_col not in df.columns:
        raise ValueError(
            f"La colonna label '{label_col}' non è presente nel DataFrame."
        )

    if feature_cols is None:
        # Usiamo un set minimo di feature numeriche (puoi estenderlo in futuro)
        feature_cols = ["total_minutes", "timestep_minutes"]

    for col in feature_cols:
        if col not in df.columns:
            raise ValueError(
                f"La colonna di feature '{col}' non è presente nel DataFrame."
            )

    X = df[feature_cols].copy()
    y = df[label_col].astype(int).copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y if y.nunique() > 1 else None,
    )

    return X_train, X_test, y_train, y_test
