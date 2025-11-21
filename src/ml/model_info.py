from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import json


def load_model_report(model_path: str | Path) -> Dict[str, Any]:
    """Carica il report JSON associato al modello.

    Esempio:
    - model_path: "models/risk_model.pkl" → report: "models/risk_model.report.json"
    """
    path = Path(model_path)
    report_path = path.with_suffix(".report.json")
    if not report_path.exists():
        raise FileNotFoundError(f"Report del modello non trovato: {report_path}")

    with report_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_model_version(model_path: str | Path) -> str | None:
    """Ritorna la versione del modello leggendo il report JSON.

    Se il campo non esiste, restituisce None.
    """
    try:
        report = load_model_report(model_path)
    except FileNotFoundError:
        return None

    return report.get("model_version")