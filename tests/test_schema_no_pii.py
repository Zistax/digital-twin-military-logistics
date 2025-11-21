from pathlib import Path

import pandas as pd


# Nomi colonna vietati (chiaramente PII)
PII_BANNED_COLUMNS = {
    "name",
    "first_name",
    "last_name",
    "email",
    "phone",
    "plate",
    "license_plate",
    "cf",
    "codice_fiscale",
}


def test_convoy_risk_dataset_has_no_pii_columns():
    """Il dataset principale di rischio non deve contenere colonne chiaramente PII."""
    dataset_path = Path("data/processed/convoy_risk_dataset.csv")
    if not dataset_path.exists():
        # Se il dataset non esiste, saltiamo il test (oppure falliamo, in base a come preferisci).
        return

    df = pd.read_csv(dataset_path)
    cols = {c.lower() for c in df.columns}

    assert PII_BANNED_COLUMNS.isdisjoint(
        cols
    ), f"Trovate colonne potenzialmente PII nel dataset di rischio: {PII_BANNED_COLUMNS & cols}"

def test_events_logs_have_no_pii_columns():
    """I file di log eventi non devono avere colonne chiaramente PII."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        return

    # Cerchiamo file che finiscono con _events.csv
    for csv_path in raw_dir.glob("*_events.csv"):
        df = pd.read_csv(csv_path)
        cols = {c.lower() for c in df.columns}

        assert PII_BANNED_COLUMNS.isdisjoint(
            cols
        ), f"File {csv_path} contiene colonne potenzialmente PII: {PII_BANNED_COLUMNS & cols}"