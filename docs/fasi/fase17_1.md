# Fase 17 – Monitoraggio modello & drift (Parte 1, Giorni 1–3, Windows)

> **Obiettivo pratico (Parte 1)**  
> Creare i primi strumenti per **monitorare il modello di rischio** nel tempo:
>
> - calcolare un indicatore di **drift sui dati** (PSI),
> - confrontare le performance del modello su dataset “vecchio” vs “corrente”,
> - salvare un **report JSON** in `data/monitoring/reports`.

Non facciamo ancora retraining automatico: qui prepari solo le **misure**.

> **Prerequisiti:**
> - Modello di rischio già addestrato (`models/risk_model.pkl` esiste),
> - dataset base `data/processed/convoy_risk_dataset.csv` esiste,
> - Fase 13 completata (data contracts) e Fase 16 (CI) almeno impostata.


---

## Struttura Fase 17 – Parte 1

- **Giorno 1** – Cartella `data/monitoring` + modulo `drift_monitor.py` (PSI)
- **Giorno 2** – Script `run_drift_check.py` (PSI per feature + setup snapshot corrente)
- **Giorno 3** – Aggiungere metriche modello (AUC, Brier) e report JSON completo


---

## Giorno 1 – Struttura `data/monitoring` + `drift_monitor.py` (PSI base)

### Obiettivo del giorno
- Preparare la cartella `data/monitoring`,
- creare il modulo `src/ml/drift_monitor.py`,
- implementare una funzione `compute_psi` riutilizzabile.


---

### 1. Creare la cartella `data/monitoring`

1. In **Esplora File** o **VS Code**, nella root del progetto, crea le cartelle:

   - `data/monitoring`
   - `data/monitoring/reports`

Oppure da terminale (PowerShell o cmd), dalla root del progetto:

```bash
mkdir data\monitoring
mkdir data\monitoring\reports
```

Per i test iniziali userai anche un file “corrente”:

- `data/monitoring/convoy_risk_dataset_current.csv`

> All’inizio puoi semplicemente **copiare** il dataset di training come snapshot corrente.

Da terminale (cmd):

```bash
copy data\processed\convoy_risk_dataset.csv data\monitoring\convoy_risk_dataset_current.csv
```

Oppure con Esplora File: copia/incolla e rinomina.

**Checklist**
- [ ] Esiste `data/monitoring`
- [ ] Esiste `data/monitoring/reports`
- [ ] Esiste `data/monitoring/convoy_risk_dataset_current.csv` (per ora copia del dataset base)


---

### 2. Creare `src\ml\drift_monitor.py` con `compute_psi`

1. In **VS Code**, espandi `src/ml`.
2. Crea il file:

   - `src/ml/drift_monitor.py`

3. Inserisci questo codice:

```python
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


def compute_psi(
    ref: Iterable[float],
    cur: Iterable[float],
    n_bins: int = 10,
) -> float:
    """Calcola il Population Stability Index (PSI) tra due distribuzioni numeriche.

    - ref: valori di riferimento (es. dataset di training).
    - cur: valori correnti (es. nuovo dataset).
    - n_bins: numero di bin per l'istogramma.

    Ritorna un valore >= 0:
    - ~0.0–0.1  → drift trascurabile
    - ~0.1–0.2  → drift moderato (monitorare)
    - > 0.2     → drift significativo
    """
    ref_s = pd.Series(list(ref)).dropna()
    cur_s = pd.Series(list(cur)).dropna()

    if ref_s.empty or cur_s.empty:
        return 0.0

    # Se i valori sono costanti, il PSI e' 0 (nessuna informazione)
    if ref_s.nunique() == 1 and cur_s.nunique() == 1:
        return 0.0

    # Creiamo bin sulla base della distribuzione di riferimento
    bins = np.linspace(ref_s.min(), ref_s.max(), n_bins + 1)

    ref_counts, _ = np.histogram(ref_s, bins=bins)
    cur_counts, _ = np.histogram(cur_s, bins=bins)

    # Convertiamo in percentuali
    ref_perc = ref_counts / (ref_counts.sum() or 1)
    cur_perc = cur_counts / (cur_counts.sum() or 1)

    # Evitiamo divisioni per 0
    ref_perc = np.where(ref_perc == 0, 1e-6, ref_perc)
    cur_perc = np.where(cur_perc == 0, 1e-6, cur_perc)

    psi_values = (cur_perc - ref_perc) * np.log(cur_perc / ref_perc)
    psi = float(np.sum(psi_values))

    return psi


def compute_dataset_psi(
    ref_df: pd.DataFrame,
    cur_df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    label_col: str = "failure",
    n_bins: int = 10,
) -> Dict[str, float]:
    """Calcola il PSI per ogni colonna numerica in feature_cols.

    - ref_df: DataFrame di riferimento (es. Gold di training).
    - cur_df: DataFrame corrente (es. snapshot recente).
    - feature_cols: lista opzionale di colonne da analizzare. Se None, usa
      tutte le colonne numeriche tranne `label_col`.
    - label_col: nome della colonna target da escludere.
    """
    if feature_cols is None:
        numeric_cols = ref_df.select_dtypes(include=["number"]).columns.tolist()
        feature_cols = [c for c in numeric_cols if c != label_col]

    psi_by_feature: Dict[str, float] = {}

    for col in feature_cols:
        if col not in ref_df.columns or col not in cur_df.columns:
            continue

        psi_val = compute_psi(ref_df[col], cur_df[col], n_bins=n_bins)
        psi_by_feature[col] = psi_val

    return psi_by_feature
```

4. Salva il file.

**Checklist**
- [ ] Esiste `src/ml/drift_monitor.py`
- [ ] La funzione `compute_psi` è definita
- [ ] La funzione `compute_dataset_psi` è definita


---

### 3. Test rapido della funzione `compute_psi` da REPL

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python
```

2. Nel prompt Python:

```python
from src.ml.drift_monitor import compute_psi

# Due distribuzioni molto simili: PSI piccolo
psi_small = compute_psi([1, 2, 3, 4, 5], [1.1, 2.1, 3.1, 4.1, 5.1])
print("PSI (simile):", psi_small)

# Due distribuzioni molto diverse: PSI piu' grande
psi_big = compute_psi([1, 1, 1, 1, 1], [10, 10, 10, 10, 10])
print("PSI (diverso):", psi_big)
```

3. Dovresti vedere un valore piccolo (vicino a 0) per `psi_small` e più grande per `psi_big`.

4. Esci dal REPL:

```python
exit()
```

**Checklist (fine Giorno 1)**
- [ ] `compute_psi` funziona e produce valori diversi per distribuzioni diverse
- [ ] `compute_dataset_psi` è pronta da usare sui dataset reali
- [ ] Esiste `data/monitoring/convoy_risk_dataset_current.csv` per i test iniziali


---

## Giorno 2 – Script `run_drift_check.py` (PSI per il dataset)


### Obiettivo del giorno
- Creare uno script da riga di comando:
  - confronta `convoy_risk_dataset.csv` (riferimento) e lo snapshot corrente,
  - calcola il PSI per ogni feature numerica,
  - stampa un riepilogo leggibile.


---

### 1. Creare `src\ml\run_drift_check.py`

1. In **VS Code**, in `src/ml`, crea il file:

   - `run_drift_check.py`

2. Inserisci questo codice iniziale (senza ancora le metriche del modello):

```python
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict

import json
import pandas as pd

from src.ml.drift_monitor import compute_dataset_psi


BASE_DIR = Path(".")
REF_DATASET_PATH = BASE_DIR / "data" / "processed" / "convoy_risk_dataset.csv"
CURR_DATASET_PATH = BASE_DIR / "data" / "monitoring" / "convoy_risk_dataset_current.csv"
REPORTS_DIR = BASE_DIR / "data" / "monitoring" / "reports"


def run_drift_check() -> Dict[str, float]:
    """Esegue il calcolo del PSI per ogni feature numerica.

    Per ora:
    - legge il dataset di riferimento e quello corrente,
    - calcola il PSI per ogni feature,
    - stampa un riepilogo,
    - (nella prossima giornata) salveremo anche un report JSON piu' ricco.
    """
    if not REF_DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset di riferimento non trovato: {REF_DATASET_PATH}")

    if not CURR_DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset corrente non trovato: {CURR_DATASET_PATH}\n"
                                "Crea o copia un file in quella posizione prima di lanciare il check.")

    df_ref = pd.read_csv(REF_DATASET_PATH)
    df_cur = pd.read_csv(CURR_DATASET_PATH)

    psi_by_feature = compute_dataset_psi(df_ref, df_cur, label_col="failure")

    print("=== Drift check (solo PSI per feature) ===")
    for col, psi in sorted(psi_by_feature.items(), key=lambda x: x[0]):
        status = "OK"
        if psi > 0.2:
            status = "DRIFT"
        elif psi > 0.1:
            status = "ATTENZIONE"
        print(f"- {col:30s} PSI={psi:.3f} [{status}]")

    return psi_by_feature


def main() -> None:
    run_drift_check()


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/ml/run_drift_check.py` con la funzione `run_drift_check`


---

### 2. Prova veloce dello script da linea di comando

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python -m src.ml.run_drift_check
```

2. Dovresti vedere un output del tipo:

```text
=== Drift check (solo PSI per feature) ===
- total_minutes                 PSI=0.000 [OK]
- timestep_minutes              PSI=0.000 [OK]
- max_risk_eff                  PSI=0.012 [OK]
...
```

> Dato che, per ora, il dataset “corrente” è solo una copia di quello di riferimento,
> i PSI dovrebbero essere molto vicini a 0.

**Checklist (fine Giorno 2)**
- [ ] `python -m src.ml.run_drift_check` gira senza errori
- [ ] Vedi la lista delle feature e il PSI per ciascuna


---

## Giorno 3 – Aggiungere metriche modello (AUC, Brier) e report JSON


### Obiettivo del giorno
- Estendere `run_drift_check.py` per:
  - valutare il modello su **dataset di riferimento** e **corrente**,
  - salvare un report JSON in `data/monitoring/reports` con:
    - PSI per feature,
    - metriche modello (AUC, Brier) su ref e current,
    - differenze tra le metriche.


---

### 1. Aggiungere funzioni di valutazione modello in `drift_monitor.py`

1. Apri `src/ml/drift_monitor.py`.
2. In fondo al file, **sotto** `compute_dataset_psi`, aggiungi:

```python
from typing import Any

import joblib
from sklearn.metrics import brier_score_loss, roc_auc_score


def evaluate_model_on_dataset(
    model_path: Path,
    dataset_path: Path,
    label_col: str = "failure",
) -> Dict[str, Any]:
    """Valuta il modello di rischio su un dataset CSV.

    Ritorna un dict con:
    - auc
    - brier
    - n_samples
    """
    if not model_path.exists():
        raise FileNotFoundError(f"Modello non trovato: {model_path}")

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset non trovato: {dataset_path}")

    df = pd.read_csv(dataset_path)

    if label_col not in df.columns:
        raise ValueError(f"Colonna target '{label_col}' mancante in {dataset_path}")

    y_true = df[label_col].astype(int)
    X = df.drop(columns=[label_col])

    model = joblib.load(model_path)
    # Supponiamo che il modello abbia un metodo predict_proba
    y_proba = model.predict_proba(X)[:, 1]

    auc = roc_auc_score(y_true, y_proba)
    brier = brier_score_loss(y_true, y_proba)

    return {
        "auc": float(auc),
        "brier": float(brier),
        "n_samples": int(len(df)),
    }
```

3. Salva il file.

**Checklist**
- [ ] `drift_monitor.py` contiene `evaluate_model_on_dataset`


---

### 2. Estendere `run_drift_check.py` per usare le metriche e salvare JSON

1. Apri `src/ml/run_drift_check.py`.
2. Aggiorna gli import in testa al file, aggiungendo:

```python
from src.ml.drift_monitor import compute_dataset_psi, evaluate_model_on_dataset
```

3. Sotto le costanti esistenti, aggiungi:

```python
MODEL_PATH = BASE_DIR / "models" / "risk_model.pkl"
```

4. Modifica la funzione `run_drift_check` in questo modo (sostituisci il corpo con la versione seguente):

```python
def run_drift_check() -> Dict[str, float]:
    """Esegue il calcolo del PSI e delle metriche modello, e salva un report JSON."""
    if not REF_DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset di riferimento non trovato: {REF_DATASET_PATH}")

    if not CURR_DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset corrente non trovato: {CURR_DATASET_PATH}\n"
            "Crea o copia un file in quella posizione prima di lanciare il check."
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    df_ref = pd.read_csv(REF_DATASET_PATH)
    df_cur = pd.read_csv(CURR_DATASET_PATH)

    # 1) PSI per feature
    psi_by_feature = compute_dataset_psi(df_ref, df_cur, label_col="failure")

    # 2) Metriche modello su dataset di riferimento e corrente
    metrics_ref = evaluate_model_on_dataset(MODEL_PATH, REF_DATASET_PATH, label_col="failure")
    metrics_cur = evaluate_model_on_dataset(MODEL_PATH, CURR_DATASET_PATH, label_col="failure")

    delta_auc = metrics_cur["auc"] - metrics_ref["auc"]
    delta_brier = metrics_cur["brier"] - metrics_ref["brier"]

    # 3) Costruiamo il report
    ts_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    report = {
        "timestamp_utc": ts_utc,
        "paths": {
            "ref_dataset": str(REF_DATASET_PATH),
            "current_dataset": str(CURR_DATASET_PATH),
            "model": str(MODEL_PATH),
        },
        "psi": psi_by_feature,
        "metrics": {
            "ref": metrics_ref,
            "current": metrics_cur,
            "delta": {
                "auc": float(delta_auc),
                "brier": float(delta_brier),
            },
        },
    }

    # 4) Salviamo il report JSON
    filename = f"drift_{ts_utc.replace(':', '').replace('-', '')}.json"
    report_path = REPORTS_DIR / filename
    latest_path = REPORTS_DIR / "drift_latest.json"

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    with latest_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # 5) Stampa di riepilogo
    print("=== Drift & performance check ===")
    print(f"- Ref dataset:     {REF_DATASET_PATH}")
    print(f"- Current dataset: {CURR_DATASET_PATH}")
    print(f"- Model:           {MODEL_PATH}")
    print()
    print("PSI per feature (ordinato per PSI decrescente):")
    for col, psi in sorted(psi_by_feature.items(), key=lambda x: x[1], reverse=True):
        status = "OK"
        if psi > 0.2:
            status = "DRIFT"
        elif psi > 0.1:
            status = "ATTENZIONE"
        print(f"  {col:30s} PSI={psi:.3f} [{status}]")

    print()
    print("Metriche modello:")
    print(f"  AUC ref     = {metrics_ref['auc']:.3f}")
    print(f"  AUC current = {metrics_cur['auc']:.3f}  (delta={delta_auc:+.3f})")
    print(f"  Brier ref   = {metrics_ref['brier']:.3f}")
    print(f"  Brier curr  = {metrics_cur['brier']:.3f} (delta={delta_brier:+.3f})")
    print()
    print(f"Report salvato in: {report_path}")
    print(f"Report 'latest'   : {latest_path}")

    return psi_by_feature
```

5. Salva il file.

**Checklist**
- [ ] `run_drift_check` ora usa anche `evaluate_model_on_dataset`
- [ ] Viene creato un JSON in `data/monitoring/reports`


---

### 3. Eseguire il nuovo drift check con report JSON

1. Nel terminale, dalla root del progetto:

```bash
python -m src.ml.run_drift_check
```

2. Controlla l’output a video (PSI + metriche AUC/Brier).  
3. Controlla che in `data/monitoring/reports` siano stati creati:

   - un file tipo `drift_20251116T123000Z.json`
   - un file `drift_latest.json`

4. Apri `drift_latest.json` con VS Code e verifica la struttura (sezioni `psi`, `metrics.ref`, `metrics.current`, `metrics.delta`).

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] `python -m src.ml.run_drift_check` gira senza errori
- [ ] Esiste `data/monitoring/reports/drift_latest.json`
- [ ] Il report contiene PSI per feature e metriche modello ref/current

---

Con questa Parte 1 hai:

- una **funzione PSI** riutilizzabile,
- uno script per confrontare dataset di riferimento e corrente,
- un **report JSON** completo (PSI + AUC + Brier) pronto per guidare decisioni di retraining.

Nella **Parte 2** (file `fase17_2.md`) userai questo report per prendere decisioni
(“serve retraining sì/no?”) e aggiornerai la documentazione.
