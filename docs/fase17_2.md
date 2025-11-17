# Fase 17 – Monitoraggio modello & drift (Parte 2, Giorni 4–6, Windows)

> **Obiettivo pratico (Parte 2)**  
> Usare il report generato da `run_drift_check.py` per:
>
> - decidere se **raccomandare un retraining** del modello,
> - aggiungere test minimi sulle funzioni di drift,
> - documentare il flusso di monitoraggio nel `README.md`.


---

## Struttura Fase 17 – Parte 2

- **Giorno 4** – Modulo `retraining_decision.py` (logica soglie e motivazioni)
- **Giorno 5** – Test su `compute_psi` e su `decide_retraining`
- **Giorno 6** – Aggiornare README (Drift & Retraining manuale) e giro completo


---

## Giorno 4 – Modulo `retraining_decision.py`

### Obiettivo del giorno
- Creare un piccolo modulo che:
  - legge `data/monitoring/reports/drift_latest.json`,
  - applica soglie (PSI, AUC, Brier),
  - stampa un riepilogo leggibile,
  - restituisce una struttura con `retrain_recommended: bool`.


---

### 1. Creare `src\ml\retraining_decision.py`

1. In **VS Code**, nella cartella `src/ml`, crea il file:

   - `retraining_decision.py`

2. Inserisci il seguente codice:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import json


DEFAULT_REPORT_PATH = Path("data") / "monitoring" / "reports" / "drift_latest.json"


def load_drift_report(path: Path | None = None) -> Dict[str, Any]:
    """Carica il report di drift da JSON."""
    report_path = path or DEFAULT_REPORT_PATH
    if not report_path.exists():
        raise FileNotFoundError(f"Report di drift non trovato: {report_path}")

    with report_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def decide_retraining(
    report: Dict[str, Any],
    psi_threshold: float = 0.2,
    auc_drop_threshold: float = -0.05,
    brier_increase_threshold: float = 0.02,
) -> Dict[str, Any]:
    """Decide se raccomandare il retraining in base a drift & metriche.

    - psi_threshold: soglia oltre la quale consideriamo il drift significativo.
    - auc_drop_threshold: massimo delta AUC accettabile (current - ref). Se minore o
      uguale a questa soglia (es. -0.05 = calo di 5 punti), segnala problema.
    - brier_increase_threshold: massimo aumento Brier accettabile.

    Ritorna un dict con:
    - retrain_recommended: bool
    - max_psi: float
    - delta_auc: float
    - delta_brier: float
    - reasons: lista di stringhe che spiegano il perche'.
    """
    psi_by_feature = report.get("psi", {}) or {}
    max_psi = max(psi_by_feature.values()) if psi_by_feature else 0.0

    metrics_delta = report.get("metrics", {}).get("delta", {})
    delta_auc = float(metrics_delta.get("auc", 0.0))
    delta_brier = float(metrics_delta.get("brier", 0.0))

    reasons: List[str] = []

    if max_psi > psi_threshold:
        reasons.append(
            f"PSI massimo {max_psi:.3f} supera la soglia {psi_threshold:.3f}."
        )

    if delta_auc <= auc_drop_threshold:
        reasons.append(
            f"Delta AUC {delta_auc:+.3f} peggiore del limite {auc_drop_threshold:+.3f}."
        )

    if delta_brier >= brier_increase_threshold:
        reasons.append(
            f"Delta Brier {delta_brier:+.3f} peggiore del limite {brier_increase_threshold:+.3f}."
        )

    retrain = len(reasons) > 0

    return {
        "retrain_recommended": retrain,
        "max_psi": float(max_psi),
        "delta_auc": delta_auc,
        "delta_brier": delta_brier,
        "reasons": reasons,
    }


def main() -> None:
    report = load_drift_report()
    decision = decide_retraining(report)

    print("=== Decisione retraining modello rischio ===")
    print(f"PSI massimo:    {decision['max_psi']:.3f}")
    print(f"Delta AUC:      {decision['delta_auc']:+.3f}")
    print(f"Delta Brier:    {decision['delta_brier']:+.3f}")
    print()

    if decision["retrain_recommended"]:
        print(">>> ATTENZIONE: si consiglia di pianificare un retraining del modello.")
        print("Motivazioni:")
        for reason in decision["reasons"]:
            print(f"- {reason}")
    else:
        print("Nessuna soglia critica superata. Retraining non strettamente necessario per ora.")


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/ml/retraining_decision.py`
- [ ] La funzione `decide_retraining` applica le soglie PSI/AUC/Brier
- [ ] Il `main()` stampa un riepilogo chiaro


---

### 2. Prova veloce della decisione di retraining

1. Assicurati di avere un report aggiornato (se serve rilancia `run_drift_check`):

```bash
python -m src.ml.run_drift_check
```

2. Poi esegui:

```bash
python -m src.ml.retraining_decision
```

3. Dovresti vedere un output del tipo:

```text
=== Decisione retraining modello rischio ===
PSI massimo:    0.012
Delta AUC:      +0.000
Delta Brier:    +0.000

Nessuna soglia critica superata. Retraining non strettamente necessario per ora.
```

> Finché usi come “current” una copia del dataset di riferimento, è normale che
> non ci sia drift e che le metriche siano identiche.

**Checklist (fine Giorno 4)**
- [ ] `python -m src.ml.retraining_decision` gira senza errori
- [ ] Il messaggio di decisione è coerente con il report `drift_latest.json`


---

## Giorno 5 – Test per PSI e decisione retraining

### Obiettivo del giorno
- Aggiungere test automatici per:
  - funzione `compute_psi`,
  - funzione `decide_retraining` con un report sintetico.


---

### 1. Test per `compute_psi`

1. In **VS Code**, nella cartella `tests`, crea il file:

   - `test_drift_monitor.py`

2. Inserisci questo contenuto:

```python
from src.ml.drift_monitor import compute_psi


def test_compute_psi_changes_with_distribution():
    # Stessa distribuzione -> PSI molto piccolo (quasi 0)
    psi_same = compute_psi([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    # Distribuzioni diverse -> PSI piu' grande
    psi_diff = compute_psi([1, 1, 1, 1, 1], [10, 10, 10, 10, 10])

    assert psi_same >= 0.0
    assert psi_diff >= 0.0
    assert psi_diff > psi_same
```

3. Salva il file.

**Checklist**
- [ ] Esiste `tests/test_drift_monitor.py` con almeno un test per `compute_psi`


---

### 2. Test per `decide_retraining`

1. Sempre in `tests`, crea il file `test_retraining_decision.py`.
2. Inserisci:

```python
from src.ml.retraining_decision import decide_retraining


def test_decide_retraining_flags_when_thresholds_exceeded():
    # Report sintetico con PSI alto e delta metriche peggiorativi
    report = {
        "psi": {"feature1": 0.25},
        "metrics": {
            "delta": {
                "auc": -0.10,
                "brier": 0.05,
            }
        },
    }

    decision = decide_retraining(report)

    assert decision["retrain_recommended"] is True
    assert len(decision["reasons"]) >= 1


def test_decide_retraining_ok_when_all_good():
    report = {
        "psi": {"feature1": 0.05},
        "metrics": {
            "delta": {
                "auc": 0.0,
                "brier": 0.0,
            }
        },
    }

    decision = decide_retraining(report)

    assert decision["retrain_recommended"] is False
```

3. Salva il file.

**Checklist**
- [ ] Esiste `tests/test_retraining_decision.py` con i due test base


---

### 3. Eseguire i test

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest tests/test_drift_monitor.py tests/test_retraining_decision.py
```

Oppure, per tutta la suite:

```bash
pytest
```

Assicurati che tutti i test passino.

**Checklist (fine Giorno 5)**
- [ ] I test per drift e retraining decision passano
- [ ] Nessun test precedente è stato rotto dalle modifiche


---

## Giorno 6 – Documentare Drift & Retraining nel README

### Obiettivo del giorno
- Aggiungere una sezione dedicata nel `README.md` che spieghi:
  - come lanciare il drift check,
  - dove trovare i report,
  - come usare `retraining_decision`.


---

### 1. Aggiornare il README

1. Apri `README.md`.
2. Aggiungi una sezione simile (adatta i nomi se hai personalizzato qualcosa):

```markdown
## Monitoraggio modello & Drift

Per monitorare nel tempo la stabilita' del modello di rischio viene utilizzato un
flusso di drift & performance check basato su:

- dataset di riferimento (ad es. `data/processed/convoy_risk_dataset.csv`)
- dataset corrente/snapshot (ad es. `data/monitoring/convoy_risk_dataset_current.csv`)
- modello addestrato (`models/risk_model.pkl`)

Strumenti principali:

- `python -m src.ml.run_drift_check`  
  Calcola il **PSI** per le feature numeriche e valuta il modello su dataset
  di riferimento e corrente (AUC, Brier). I risultati vengono salvati in:

  - `data/monitoring/reports/drift_YYYYMMDDTHHMMSSZ.json`
  - `data/monitoring/reports/drift_latest.json`

- `python -m src.ml.retraining_decision`  
  Legge `drift_latest.json`, applica soglie di drift e degradazione metrica
  (PSI > 0.2, calo AUC, aumento Brier) e segnala se e' consigliato pianificare
  un **retraining** del modello di rischio.
```

3. Salva il file.

**Checklist**
- [ ] Il README contiene una sezione “Monitoraggio modello & Drift” chiara


---

### 2. Giro completo di verifica

1. Rigenera (se vuoi) un report di drift:

```bash
python -m src.ml.run_drift_check
```

2. Esegui la decisione di retraining:

```bash
python -m src.ml.retraining_decision
```

3. Esegui i test (almeno drift + retraining decision, meglio tutta la suite):

```bash
pytest
```

4. Se tutto è ok, fai il commit Git:

```bash
git add src/ml/drift_monitor.py src/ml/run_drift_check.py src/ml/retraining_decision.py tests/test_drift_monitor.py tests/test_retraining_decision.py README.md
git commit -m "Fase 17: monitoraggio modello e drift (PSI, metriche, decisione retraining)"
git push
```

**Checklist (fine Giorno 6 – fine Fase 17)**
- [ ] Script di drift check (`run_drift_check.py`) funzionante e testato
- [ ] Modulo decisione retraining (`retraining_decision.py`) funzionante e testato
- [ ] README aggiornato con istruzioni per drift & retraining
- [ ] Commit Git creato per chiudere la Fase 17


---

Con la Fase 17 hai aggiunto un livello importante di **monitoraggio del modello**:

- misuri quanto i dati “nuovi” si discostano da quelli di training (PSI),
- controlli se le performance del modello stanno degradando (AUC, Brier),
- hai una decisione guidata su quando conviene **riaddestrare** il modello.

Questo è un passo chiave verso un flusso MLOps più maturo, pronto per fasi successive
in cui potresti automatizzare il retraining o introdurre champion/challenger.
