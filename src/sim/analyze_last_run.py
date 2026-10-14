from __future__ import annotations

from pathlib import Path

from .metrics import load_events_csv, compute_basic_kpis


def find_latest_events_csv(raw_dir: str | Path = "data/raw") -> Path:
    """Trova l'ultimo file sim_events_*.csv nella cartella data/raw.

    Ritorna il percorso del file più recente (in base al nome).
    """
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        raise FileNotFoundError(f"La cartella non esiste: {raw_path}")

    csv_files = sorted(raw_path.glob("sim_events_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"Nessun file sim_events_*.csv trovato in {raw_path}")

    return csv_files[-1]  # ultimo nella lista ordinata


def main() -> None:
    print("=== Analisi ultima simulazione (analyze_last_run.py) ===")

    latest_csv = find_latest_events_csv()
    print(f"Ultimo file di eventi trovato: {latest_csv}")

    df = load_events_csv(latest_csv)
    kpis = compute_basic_kpis(df)

    print()
    print("=== KPI di base ===")
    print(f"Numero convogli:             {kpis['n_convoys']}")
    print(f"Convogli completati:         {kpis['n_completed_convoys']}")
    print(f"Convogli non completati:     {kpis['n_not_completed_convoys']}")

    if kpis["avg_completion_minute"] is not None:
        print(f"Minuto medio completamento:  {kpis['avg_completion_minute']:.1f}")
        print(f"Minuto minimo completamento: {kpis['min_completion_minute']:.1f}")
        print(f"Minuto massimo completamento:{kpis['max_completion_minute']:.1f}")
    else:
        print(
            (
                "Nessun convoglio completato: impossibile "
                "calcolare i tempi di completamento."
            )
        )

    print()
    print("Analisi completata.")


if __name__ == "__main__":
    main()
