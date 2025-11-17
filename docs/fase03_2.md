# Fase 03 – Analisi log e KPI base (Windows) – Parte 2 (Giorni 5–7)

> **Scopo Parte 2**  
> Spostare la logica di calcolo dei KPI dal notebook a un **modulo Python riutilizzabile**, creare **test automatici** e uno **script da console** per analizzare rapidamente l’ultimo CSV generato.

In questa Parte 2 farai:

- Giorno 5 – Creare il modulo `metrics.py` in `src\sim`
- Giorno 6 – Creare uno script da console `analyze_last_run.py`
- Giorno 7 – Aggiungere test per le metriche e fare un commit Git di fine Fase 03

> Assicurati di aver completato la **Parte 1** (`fase03_1.md`) e di avere il notebook con il codice dei KPI funzionante.

---

## Giorno 5 – Creare il modulo `metrics.py` (funzioni KPI riutilizzabili)

### Obiettivo del giorno
Creare un file `src\sim\metrics.py` con funzioni Python per:
- caricare un CSV di eventi,
- calcolare i KPI base.

---

### 1. Creare il file `metrics.py`

1. Apri **VS Code**.
2. Nella barra laterale, espandi `src` → `sim`.
3. Crea un nuovo file chiamato `metrics.py`.
4. Inserisci il seguente contenuto:

```python
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
```

5. Salva il file.

**Checklist**
- [x] Esiste `src\sim\metrics.py`
- [x] Il file contiene le funzioni `load_events_csv` e `compute_basic_kpis`

---

### 2. Provare le funzioni in un piccolo script (opzionale ma consigliato)

1. Nel terminale (con `.venv` attivo), apri Python interattivo:

```bash
python
```

2. Dentro il REPL Python, prova:

```python
from src.sim.metrics import load_events_csv, compute_basic_kpis

df = load_events_csv("data/raw/sim_events_20251117_152933.csv")  # <-- metti un tuo file
kpis = compute_basic_kpis(df)
print(kpis)
```

3. Verifica che il dizionario `kpis` abbia valori coerenti.

4. Esci dal REPL con:

```python
exit()
```

**Checklist (fine Giorno 5)**
- [x] `metrics.py` è importabile senza errori
- [x] `load_events_csv` carica un CSV reale
- [x] `compute_basic_kpis` restituisce un dizionario con i KPI

---

## Giorno 6 – Script da console `analyze_last_run.py`

### Obiettivo del giorno
Creare uno script `src\sim\analyze_last_run.py` che:
- trova l’ultimo file `sim_events_*.csv` in `data\raw`,
- lo carica,
- calcola i KPI,
- stampa un riassunto a schermo.

Lo userai per analizzare velocemente l’ultima simulazione senza aprire Jupyter.

---

### 1. Creare il file `analyze_last_run.py`

1. In VS Code, sotto `src\sim`, crea il file `analyze_last_run.py`.
2. Inserisci il seguente contenuto:

```python
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

    if kpis['avg_completion_minute'] is not None:
        print(f"Minuto medio completamento:  {kpis['avg_completion_minute']:.1f}")
        print(f"Minuto minimo completamento: {kpis['min_completion_minute']:.1f}")
        print(f"Minuto massimo completamento:{kpis['max_completion_minute']:.1f}")
    else:
        print("Nessun convoglio completato: impossibile calcolare i tempi di completamento.")

    print()
    print("Analisi completata.")


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [x] Esiste `src\sim\analyze_last_run.py`
- [x] Lo script importa `load_events_csv` e `compute_basic_kpis`

---

### 2. Eseguire lo script di analisi dal terminale

1. Nel terminale (con `.venv` attivo), assicurati di essere nella cartella del progetto.
2. Genera prima un nuovo CSV (se non l’hai già fatto di recente):

```bash
python -m src.sim.main_sim
```

3. Poi esegui lo script di analisi:

```bash
python -m src.sim.analyze_last_run
```

4. Dovresti vedere:

- il percorso dell’ultimo file `sim_events_*.csv` in `data\raw`,
- i KPI calcolati,
- eventuali messaggi finali.

**Checklist (fine Giorno 6)**
- [x] `python -m src.sim.analyze_last_run` funziona senza errori
- [x] Lo script individua l’ultimo CSV (anche se ce ne sono più di uno)
- [x] I KPI stampati hanno senso rispetto alla simulazione eseguita

---

## Giorno 7 – Test per le metriche e commit Git fine Fase 03

### Obiettivo del giorno
- Aggiungere test automatici per le funzioni in `metrics.py`
- Eseguire `pytest`
- Fare un commit Git che chiude la Fase 03

---

### 1. Creare il file di test `tests\test_metrics_basic.py`

1. In VS Code, nella cartella `tests`, crea il file `test_metrics_basic.py`.
2. Inserisci il seguente contenuto:

```python
import pandas as pd

from src.sim.metrics import compute_basic_kpis


def test_compute_basic_kpis_all_completed():
    """Tutti i convogli completano la missione."""
    data = [
        {"event_type": "convoy_spawned", "convoy_id": 1, "minute": 0},
        {"event_type": "convoy_spawned", "convoy_id": 2, "minute": 0},
        {"event_type": "convoy_completed", "convoy_id": 1, "minute": 30},
        {"event_type": "convoy_completed", "convoy_id": 2, "minute": 40},
    ]
    df = pd.DataFrame(data)

    kpis = compute_basic_kpis(df)

    assert kpis["n_convoys"] == 2
    assert kpis["n_completed_convoys"] == 2
    assert kpis["n_not_completed_convoys"] == 0
    assert kpis["min_completion_minute"] == 30.0
    assert kpis["max_completion_minute"] == 40.0


def test_compute_basic_kpis_some_not_completed():
    """Alcuni convogli non completano la missione."""
    data = [
        {"event_type": "convoy_spawned", "convoy_id": 1, "minute": 0},
        {"event_type": "convoy_spawned", "convoy_id": 2, "minute": 0},
        {"event_type": "convoy_completed", "convoy_id": 1, "minute": 30},
        # Il convoglio 2 non ha eventi di completamento
    ]
    df = pd.DataFrame(data)

    kpis = compute_basic_kpis(df)

    assert kpis["n_convoys"] == 2
    assert kpis["n_completed_convoys"] == 1
    assert kpis["n_not_completed_convoys"] == 1
    assert kpis["min_completion_minute"] == 30.0
    assert kpis["max_completion_minute"] == 30.0


def test_compute_basic_kpis_no_completed():
    """Nessun convoglio completa la missione."""
    data = [
        {"event_type": "convoy_spawned", "convoy_id": 1, "minute": 0},
        {"event_type": "convoy_spawned", "convoy_id": 2, "minute": 0},
    ]
    df = pd.DataFrame(data)

    kpis = compute_basic_kpis(df)

    assert kpis["n_convoys"] == 2
    assert kpis["n_completed_convoys"] == 0
    assert kpis["n_not_completed_convoys"] == 2
    assert kpis["avg_completion_minute"] is None
    assert kpis["min_completion_minute"] is None
    assert kpis["max_completion_minute"] is None
```

3. Salva il file.

**Checklist**
- [x] Esiste `tests\test_metrics_basic.py`
- [x] Dentro ci sono 3 funzioni di test come sopra

---

### 2. Eseguire tutti i test con `pytest`

Nel terminale (con `.venv` attivo), dalla cartella del progetto:

```bash
pytest
```

Controlla che tutti i test passino (quelli della Fase 01, Fase 02 e anche i nuovi).

**Checklist**
- [x] `pytest` gira senza errori
- [x] I test in `test_metrics_basic.py` passano

---

### 3. (Opzionale) Aggiornare `run_checks.bat` per includere `analyze_last_run`

Se vuoi, puoi modificare `run_checks.bat` per eseguire alla fine anche lo script:

```bat
python -m src.sim.analyze_last_run
```

Esempio di blocco aggiuntivo:

```bat
echo.
echo ==============================
echo Eseguo analisi dell'ultima simulazione...
echo ==============================

python -m src.sim.analyze_last_run
```

Salva il file `run_checks.bat` dopo le modifiche.

**Checklist (opzionale)**
- [x] `run_checks.bat` ora esegue anche `python -m src.sim.analyze_last_run`

---

### 4. Commit Git di fine Fase 03

1. Nel terminale, controlla lo stato:

```bash
git status
```

2. Aggiungi tutti i file modificati e creati:

```bash
git add .
```

3. Crea un commit con un messaggio chiaro, ad esempio:

```bash
git commit -m "Fase 03: analisi log, KPI base, notebook e metriche riutilizzabili"
```

4. Verifica che il working tree sia pulito:

```bash
git status
```

Dovresti vedere: `nothing to commit, working tree clean`.

**Checklist (fine Giorno 7)**
- [ ] `test_metrics_basic.py` creato
- [ ] `pytest` passa per tutti i test
- [ ] (Opzionale) `run_checks.bat` aggiornata
- [ ] Commit Git creato per la Fase 03

---

## Fine Fase 03 – Criteri di completamento

La Fase 03 è completata quando:

- [ ] So avviare Jupyter Notebook e ho il notebook `analisi_eventi_base.ipynb`
- [ ] So generare un CSV di eventi con `python -m src.sim.main_sim` e caricarlo in pandas
- [ ] Calcolo KPI di base nel notebook (Parte 1)
- [ ] Esistono i file:
  - `src\sim\metrics.py`
  - `src\sim\analyze_last_run.py`
  - `tests\test_metrics_basic.py`
- [ ] Posso eseguire `python -m src.sim.analyze_last_run` per analizzare l’ultima simulazione
- [ ] Tutti i test `pytest` passano
- [ ] Ho fatto un commit Git dedicato alla Fase 03

A questo punto sei pronto per una futura **Fase 04**, dove potrai iniziare a costruire un **primo modello di rischio** usando i dati dei log (dataset più strutturato, label, ecc.).
