Questo progetto ha l'obiettivo di creare un primo prototipo (MVP) di digital twin logistico con:

- Simulatore di convogli e depositi
- Raccolta di log e KPI
- Modello semplice di rischio
- Interfaccia utente minimale per lanciare simulazioni



## API REST rischio convoglio

Il progetto espone un'API REST locale (FastAPI) per stimare il rischio dei convogli.

- Avvio server (da root progetto, con ambiente attivo):

  ```bash
  uvicorn src.api.app:app --reload
  ```

- Endpoint principali:
  - `GET /health` → restituisce `{"status": "ok"}`
  - `POST /predict_risk` → accetta JSON con:
    - `total_minutes` (int)
    - `timestep_minutes` (int)
    - `n_convoys` (int)
    e restituisce le probabilità di rischio per ogni convoglio.

- Documentazione interattiva (Swagger UI):
  - `http://127.0.0.1:8000/docs`

## UI Web (Streamlit) – Rischio Convoglio

Per avviare una semplice interfaccia web che permette di inserire i parametri di scenario
e vedere la probabilità di rischio per ciascun convoglio:

1. Attiva l'ambiente virtuale:

   ```bash
   .venv\Scripts\activate.bat
   ```

   (oppure, in PowerShell: `.venv\Scripts\Activate.ps1`)

2. Avvia Streamlit dalla root del progetto:

   ```bash
   streamlit run src/ui/dashboard.py
   ```

3. Apri il browser all'indirizzo: <http://localhost:8501>

La pagina permette di:

- impostare `total_minutes`, `timestep_minutes`, `n_convoys`,
- calcolare le probabilità di rischio usando il modello `models/risk_model.pkl`,
- vedere una tabella ordinata per rischio e un grafico a barre,
- evidenziare i convogli con rischio maggiore di una soglia (es. 0.5).

### Soglia di rischio predefinita

Il sistema utilizza una **soglia di rischio predefinita**:

- `RISK_THRESHOLD_DEFAULT` (definita in `src/ml/risk_threshold.py`)

Questa soglia è stata scelta analizzando precision, recall e F1 nel notebook
`notebooks/evaluate_risk_model.ipynb`. Tutti i componenti (CLI, API, UI)
usano questa soglia per decidere se un convoglio è considerato "ad alto rischio".

## Configurazione & riproducibilità

Il progetto utilizza file YAML nella cartella `conf/` per gestire i valori di default:

- `conf/sim/default.yml` → parametri di simulazione (durata, timestep, n_convoys, ecc.)
- `conf/ml/default.yml` → parametri di training ML (test_size, random_state, max_iter, ecc.)

Le funzioni `load_sim_config()` e `load_ml_config()` (in `src/config/config_loader.py`)
caricano queste impostazioni. In particolare:

- il campo `random_state` in `conf/ml/default.yml` controlla la riproducibilità
  del train/test split e del modello di rischio.

Ad ogni esecuzione di `python -m src.ml.train_risk_model` viene creato/aggiornato
un file `models/risk_model.report.json` con un riepilogo dei parametri di training
e delle metriche ottenute.

## Flusso API + UI

Il progetto espone un'API FastAPI e una UI Streamlit.

### API FastAPI

- Avvio server (da root progetto, ambiente attivo):

  ```bash
  uvicorn src.api.app:app --reload
  ```

- Endpoint principali:
  - `GET /health` → stato API
  - `POST /predict` / `POST /predict_risk` → rischio convoglio
  - `POST /simulate` → esegue una simulazione e restituisce KPI di base

La documentazione interattiva è disponibile su <http://127.0.0.1:8000/docs>.

### UI Streamlit

- Avvio UI (da root progetto, ambiente attivo):

  ```bash
  streamlit run src/ui/dashboard.py
  ```

- La UI chiama l'endpoint `POST /predict` dell'API, utilizzando come URL base
  il valore configurabile nella sidebar (default `http://127.0.0.1:8000`).

Per usare correttamente la UI è necessario che il server FastAPI sia in esecuzione.

## Qualita' & Sicurezza (uso locale)

Per mantenere il progetto in buona salute è disponibile una serie di comandi:

### Controlli di qualita'

- Script Windows:

  ```bat
  run_quality.bat
  ```

Questo script:
- attiva l'ambiente `.venv`,
- esegue il linting con **Ruff** (`ruff check src tests`),
- controlla la formattazione con **Black** (`black --check src tests`),
- esegue i test con coverage (`pytest` con impostazioni da `pytest.ini`).

La coverage minima è configurata tramite `pytest.ini` (opzione `--cov-fail-under`):
se la coverage scende sotto la soglia, i test falliscono.

### Controlli di sicurezza

- Script Windows:

  ```bat
  run_security.bat
  ```

Questo script attiva `.venv` ed esegue:

- `pip-audit` per controllare se alcune dipendenze hanno vulnerabilita' note.

In caso di vulnerabilita', valuta l'aggiornamento delle versioni interessate.