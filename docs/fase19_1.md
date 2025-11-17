# Fase 19 – Retraining pipeline (Parte 1, Giorni 1–3, Windows)

> **Obiettivo pratico (Parte 1)**  
> Creare una **pipeline di retraining manuale** per il modello di rischio che:
>
> - parte da un dataset (tipicamente quello “corrente” di monitoring),
> - allena un **nuovo modello** con `train_risk_model`,
> - lo salva con un **nome versione** (timestamp),
> - lo registra nel **model registry** come *challenger*,
> - salva un **report della run** in JSON.

Questa fase **non** decide ancora la promozione a champion (lo faremo nella Parte 2).


---

## Struttura Fase 19 – Parte 1

- **Giorno 1** – Preparare cartelle e verificare gli script esistenti
- **Giorno 2** – Creare `src/ml/retrain_pipeline.py` (funzione principale)
- **Giorno 3** – Aggiungere CLI, creare una run di prova e salvare un report


---

## Giorno 1 – Preparazione cartelle e verifica prerequisiti

### Obiettivo del giorno
- Assicurarti che tutti i pezzi precedenti siano al loro posto,
- preparare le cartelle dove salverai i report di retraining.


---

### 1. Verificare che il dataset “corrente” esista

1. Controlla in **Esplora File** (o da VS Code) che esista:

   - `data/monitoring/convoy_risk_dataset_current.csv`

   Questo file lo hai creato nella **Fase 17** come snapshot dei dati “correnti”.  
   Se non esiste più, puoi ricrearlo copiando il dataset base:

   Da **cmd** o **PowerShell**, nella root del progetto:

   ```bash
   copy data\processed\convoy_risk_dataset.csv data\monitoring\convoy_risk_dataset_current.csv
   ```

2. Verifica anche che esista il dataset Gold “di riferimento”:

   - `data/processed/convoy_risk_dataset.csv`

**Checklist**
- [ ] Esiste `data/monitoring/convoy_risk_dataset_current.csv`
- [ ] Esiste `data/processed/convoy_risk_dataset.csv`


---

### 2. Verificare che `train_risk_model` funzioni ancora

Prima di costruire la pipeline, controlliamo che lo script di training base giri.

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

   ```bash
   python -m src.ml.train_risk_model
   ```

2. Dovresti vedere in output (più o meno):

   ```text
   Carico il dataset...
   Divido in train/test...
   Forma dei dataset:
     X_train: (...)
     X_test:  (...)
   ...
   Modello salvato in: models/risk_model.pkl
   ```

   E, dopo la **Fase 12**, anche la creazione di un file:

   - `models/risk_model.report.json` con dentro `model_version`, parametri e metriche.

> Se lo script dà errori, conviene prima sistemarli (seguendo le fasi precedenti) e
> solo dopo procedere con la pipeline di retraining.

**Checklist**
- [ ] `python -m src.ml.train_risk_model` gira senza errori
- [ ] Esistono `models/risk_model.pkl` e `models/risk_model.report.json`


---

### 3. Preparare la cartella per i report di retraining

Useremo la stessa cartella dei report di monitoring, per tenere tutto insieme:

- `data/monitoring/reports`

Questa l’hai già creata in Fase 17. Verifica che esista; se non c’è più, ricreala:

```bash
mkdir data\monitoring\reports
```

**Checklist (fine Giorno 1)**
- [ ] Dataset “corrente” e dataset Gold presenti
- [ ] Script `train_risk_model` funzionante
- [ ] Cartella `data/monitoring/reports` pronta per i report di retraining


---

## Giorno 2 – Creare `src/ml/retrain_pipeline.py` (logica principale)


### Obiettivo del giorno
- Creare un modulo che:
  - prende un dataset a scelta (default: quello corrente),
  - allena un nuovo modello (file `.pkl` con timestamp),
  - calcola le metriche principali (AUC, Brier),
  - registra il modello nel **model registry** come *challenger*,
  - costruisce una struttura di report in memoria (che salverai nel Giorno 3).


---

### 1. Creare il file `src\ml\retrain_pipeline.py`

1. In **VS Code**, nella cartella `src/ml`, crea il file:

   - `retrain_pipeline.py`

2. Inserisci il seguente contenuto di base:

```python
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import json

from src.ml.train_risk_model import train_risk_model
from src.ml.drift_monitor import evaluate_model_on_dataset
from src.ml.model_registry import register_model, get_champion


BASE_DIR = Path(".")
DEFAULT_DATASET_PATH = BASE_DIR / "data" / "monitoring" / "convoy_risk_dataset_current.csv"
REPORTS_DIR = BASE_DIR / "data" / "monitoring" / "reports"
MODELS_DIR = BASE_DIR / "models"


def run_retrain_pipeline(
    dataset_path: Path | None = None,
) -> Dict[str, Any]:
    """Esegue una run di retraining del modello di rischio.

    Passi:
    - usa il dataset indicato (o quello 'corrente' di default),
    - allena un nuovo modello e lo salva con nome versionato,
    - calcola le metriche (AUC, Brier) sul dataset usato,
    - registra il modello nel registry come 'challenger' (is_champion=False),
    - restituisce un dict con i dettagli della run (per report/JSON).
    """
    ds_path = dataset_path or DEFAULT_DATASET_PATH

    if not ds_path.exists():
        raise FileNotFoundError(f"Dataset per retraining non trovato: {ds_path}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Timestamp per ID modello e nome file
    ts_utc = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    model_id = f"risk_{ts_utc}"
    model_path = MODELS_DIR / f"risk_model_{ts_utc}.pkl"

    print("=== Retraining pipeline ===")
    print(f"Dataset:       {ds_path}")
    print(f"Nuovo model_id:{model_id}")
    print(f"Nuovo modello: {model_path}")
    print()

    # 1) Training del nuovo modello (usa la logica esistente)
    train_risk_model(
        dataset_path=ds_path,
        model_path=model_path,
    )

    # 2) Calcolo metriche su questo dataset
    metrics = evaluate_model_on_dataset(
        model_path=model_path,
        dataset_path=ds_path,
        label_col="failure",
    )

    print("Metriche nuovo modello su dataset di retraining:")
    print(f"  AUC:   {metrics['auc']:.3f}")
    print(f"  Brier: {metrics['brier']:.3f}")
    print(f"  n:     {metrics['n_samples']}")
    print()

    # 3) Champion attuale (se esiste)
    champion_entry = get_champion()
    champion_id = champion_entry.model_id if champion_entry is not None else None

    # 4) Registriamo il nuovo modello come challenger
    entry = register_model(
        model_id=model_id,
        model_path=model_path,
        train_dataset_path=ds_path,
        metrics=metrics,
        is_champion=False,
        notes="Modello creato dalla retraining pipeline",
    )

    print("Modello registrato nel registry come challenger.")
    if champion_id is not None:
        print(f"Champion corrente: {champion_id}")
    else:
        print("Nessun champion corrente nel registry.")

    # 5) Costruiamo un piccolo dict di report (per essere salvato come JSON)
    report: Dict[str, Any] = {
        "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_path": str(ds_path),
        "model_id": model_id,
        "model_path": str(model_path),
        "metrics": metrics,
        "champion_before": champion_id,
    }

    return report
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/ml/retrain_pipeline.py`
- [ ] La funzione `run_retrain_pipeline` allena un nuovo modello e lo registra come challenger


---

### 2. Prova veloce della pipeline (senza ancora salvare JSON)

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

   ```bash
   python
   ```

2. Nel prompt Python:

   ```python
   from pathlib import Path
   from src.ml.retrain_pipeline import run_retrain_pipeline

   report = run_retrain_pipeline()
   print("Report run:", report)
   ```

3. Dovresti vedere l’output del training (simile a `train_risk_model`) e poi la stampa di un dict tipo:

   ```text
   Report run: {
       'timestamp_utc': '2025-11-16T12:34:56Z',
       'dataset_path': 'data/monitoring/convoy_risk_dataset_current.csv',
       'model_id': 'risk_20251116T123456Z',
       'model_path': 'models/risk_model_20251116T123456Z.pkl',
       'metrics': {'auc': 0.83, 'brier': 0.17, 'n_samples': 1234},
       'champion_before': 'risk_v1'
   }
   ```

4. Esci dal REPL:

   ```python
   exit()
   ```

**Checklist (fine Giorno 2)**
- [ ] `run_retrain_pipeline()` gira senza errori
- [ ] Viene creato un nuovo file modello `models/risk_model_*.pkl`
- [ ] Il nuovo modello compare nel registry come challenger
- [ ] Il dict di report contiene dataset, model_id, metriche, champion_before


---

## Giorno 3 – Aggiungere CLI e salvataggio del report JSON

### Obiettivo del giorno
- Rendere la pipeline eseguibile da linea di comando,
- salvare automaticamente un **file JSON** per ogni run,
- avere un comando unico tipo:
  - `python -m src.ml.retrain_pipeline --dataset ...`


---

### 1. Aggiungere il `main()` con argparse in `retrain_pipeline.py`

1. Riapri `src/ml/retrain_pipeline.py`.
2. In fondo al file, **sotto** la funzione `run_retrain_pipeline`, aggiungi:

```python
def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Pipeline di retraining del modello di rischio."
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help=(
            "Percorso del dataset CSV da usare per il retraining. "
            "Se non specificato, usa il dataset corrente di monitoring."
        ),
    )

    args = parser.parse_args()
    ds_path = Path(args.dataset) if args.dataset else None

    report = run_retrain_pipeline(dataset_path=ds_path)

    # Salviamo anche un report JSON per questa run
    ts_report = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"retrain_{ts_report}.json"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / filename

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print()
    print(f"Report della run salvato in: {report_path}")


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] `retrain_pipeline.py` espone una `main()` con argparse
- [ ] La CLI accetta `--dataset` opzionale
- [ ] La run salva un file `retrain_*.json` in `data/monitoring/reports`


---

### 2. Eseguire una run di retraining da linea di comando

1. Nel terminale, dalla root del progetto:

   ```bash
   python -m src.ml.retrain_pipeline
   ```

   Questo userà di default:

   - dataset: `data/monitoring/convoy_risk_dataset_current.csv`

2. Controlla l’output console:
   - messaggi di training,
   - metriche AUC/Brier,
   - info sul champion corrente,
   - percorso del report salvato.

3. Controlla che in `data/monitoring/reports` ci sia un file tipo:

   - `retrain_20251116T123456Z.json`

   Aprilo in VS Code e verifica che contenga almeno:

   - `timestamp_utc`
   - `dataset_path`
   - `model_id`
   - `model_path`
   - `metrics` (con AUC, Brier, n_samples)
   - `champion_before`

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] `python -m src.ml.retrain_pipeline` gira senza errori
- [ ] Nuovo modello salvato con nome versionato in `models/`
- [ ] Nuovo modello registrato come challenger nel registry
- [ ] Report JSON di retraining creato in `data/monitoring/reports`

---

Con questa Parte 1 hai una **pipeline manuale di retraining** che:

- usa lo stesso dataset (o un dataset a scelta),
- allena un nuovo modello,
- lo registra come challenger nel registry,
- salva un report strutturato della run.

Nella **Parte 2** userai questa pipeline insieme al modulo **champion/challenger**
per decidere se promuovere automaticamente il nuovo modello a **champion**.
