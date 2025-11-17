from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import pandas as pd


def load_events_csv(csv_path: str | Path) -> pd.DataFrame:
    """Carica un file CSV di eventi in un DataFrame pandas."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Il file CSV non esiste: {csv_path}")

    df = pd.read_csv(csv_path)
    return df


def compute_basic_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """Calcola KPI di base a partire dal DataFrame di eventi.

    Restituisce un dizionario con, ad esempio:
    - n_convoys
    - n_completed_convoys
    - n_not_completed_convoys
    - avg_completion_minute
    - min_completion_minute
    - max_completion_minute
    """
    if "convoy_id" not in df.columns or "event_type" not in df.columns:
        raise ValueError("Il DataFrame non contiene le colonne richieste ('convoy_id', 'event_type').")

    n_convoys = int(df["convoy_id"].nunique())

    df_completed = df[df["event_type"] == "convoy_completed"]
    n_completed_convoys = int(df_completed["convoy_id"].nunique())
    n_not_completed_convoys = int(n_convoys - n_completed_convoys)

    if n_completed_convoys > 0:
        completion_minutes_by_convoy = (
            df_completed
            .groupby("convoy_id")["minute"]
            .min()
        )

        avg_completion_minute = float(completion_minutes_by_convoy.mean())
        min_completion_minute = float(completion_minutes_by_convoy.min())
        max_completion_minute = float(completion_minutes_by_convoy.max())
    else:
        avg_completion_minute = None
        min_completion_minute = None
        max_completion_minute = None

    kpis: Dict[str, Any] = {
        "n_convoys": n_convoys,
        "n_completed_convoys": n_completed_convoys,
        "n_not_completed_convoys": n_not_completed_convoys,
        "avg_completion_minute": avg_completion_minute,
        "min_completion_minute": min_completion_minute,
        "max_completion_minute": max_completion_minute,
    }

    return kpis