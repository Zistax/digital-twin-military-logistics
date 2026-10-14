from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from datetime import datetime, timezone

import csv

AUDIT_DIR = Path("data") / "audit"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def log_predict_call(payload: Dict[str, Any], response: Dict[str, Any]) -> None:
    """Logga una chiamata all'endpoint /predict in un CSV di audit.

    Il log e' pensato per fini di governance, non per PII:
    - timestamp UTC
    - parametri di input principali
    - versione modello
    - soglia utilizzata
    - numero di convogli richiesti e quanti ad alto rischio.
    """
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = AUDIT_DIR / "predict_calls.csv"

    timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    total_minutes = int(payload.get("total_minutes", 0))
    timestep_minutes = int(payload.get("timestep_minutes", 0))
    n_convoys = int(payload.get("n_convoys", 0))

    model_version = response.get("model_version")
    threshold_used = float(response.get("risk_threshold_used", 0.0))

    results = response.get("results", [])
    n_results = len(results)
    n_high_risk = sum(1 for r in results if bool(r.get("is_high_risk")))

    row = {
        "ts_utc": timestamp_utc,
        "total_minutes": total_minutes,
        "timestep_minutes": timestep_minutes,
        "n_convoys": n_convoys,
        "n_results": n_results,
        "n_high_risk": n_high_risk,
        "model_version": model_version or "",
        "risk_threshold_used": threshold_used,
    }

    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
