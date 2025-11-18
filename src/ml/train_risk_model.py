from __future__ import annotations

from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

from .dataset import load_convoy_risk_dataset, split_features_labels


def train_risk_model(
    dataset_path: str | Path = "data/processed/convoy_risk_dataset.csv",
    model_path: str | Path = "models/risk_model.pkl",
) -> None:
    """Addestra un modello di rischio semplice e lo salva su disco."""
    print("Carico il dataset...")
    df = load_convoy_risk_dataset(dataset_path)

    print("Divido in train/test...")
    X_train, X_test, y_train, y_test = split_features_labels(df)

    print("Forma dei dataset:")
    print(f"  X_train: {X_train.shape}")
    print(f"  X_test:  {X_test.shape}")

    # Modello molto semplice: Logistic Regression con parametri di default
    print("Addestro il modello (Logistic Regression)...")
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    print("Valuto il modello sul test set...")
    y_pred = model.predict(X_test)

    print("=== Confusion Matrix ===")
    print(confusion_matrix(y_test, y_pred))

    print()
    print("=== Classification Report ===")
    print(classification_report(y_test, y_pred, digits=3))

    # Salvataggio del modello
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)

    print()
    print(f"Modello salvato in: {model_path}")


def main() -> None:
    train_risk_model()


if __name__ == "__main__":
    main()