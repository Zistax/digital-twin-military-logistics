from __future__ import annotations

from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

from .dataset import load_convoy_risk_dataset, split_features_labels
from src.config.config_loader import load_ml_config

def train_risk_model(
    dataset_path: str | Path = "data/processed/convoy_risk_dataset.csv",
    model_path: str | Path = "models/risk_model.pkl",
) -> None:
    """Addestra un modello di rischio semplice e lo salva su disco."""
    print("Carico il dataset...")

    # Carichiamo la configurazione ML (test_size, random_state, ecc.)
    ml_conf = load_ml_config()

    test_size = float(ml_conf.get("test_size", 0.3))
    random_state = int(ml_conf.get("random_state", 42))
    max_iter = int(ml_conf.get("max_iter", 1000))

    df = load_convoy_risk_dataset(dataset_path)

    print("Divido in train/test...")
    X_train, X_test, y_train, y_test = split_features_labels(
        df,
        test_size=test_size,
        random_state=random_state,
    )

    print("Forma dei dataset:")
    print(f"  X_train: {X_train.shape}")
    print(f"  X_test:  {X_test.shape}")

    # Modello molto semplice: Logistic Regression con parametri di default
    print("Addestro il modello (Logistic Regression)...")
    model = LogisticRegression(max_iter=max_iter, random_state=random_state)
    model.fit(X_train, y_train)

    print("Valuto il modello sul test set...")
    y_pred = model.predict(X_test)

    print("=== Confusion Matrix ===")
    print(confusion_matrix(y_test, y_pred))

    print()
    print("=== Classification Report ===")
    print(classification_report(y_test, y_pred, digits=3))

    from datetime import datetime

    # Versione modello: timestamp ISO semplice (puoi sostituirlo con qualcosa di più evoluto in futuro)
    model_version = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    report_dict = {
        "model_version": model_version,
        "params": {
            "test_size": test_size,
            "random_state": random_state,
            "max_iter": max_iter,
        },
        "metrics": {
            "classification_report": classification_report(
                y_test, y_pred, digits=3, output_dict=True
            ),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        },
    }

    # Salvataggio del modello
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)

    # Salviamo il report come JSON accanto al modello
    import json

    report_path = model_path.with_suffix(".report.json")
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)

    print(f"Report di training salvato in: {report_path}")
    print()
    print(f"Modello salvato in: {model_path}")


def main() -> None:
    train_risk_model()


if __name__ == "__main__":
    main()