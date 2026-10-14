# Digital twin logistico

## Stato del nuovo nucleo — 14 ottobre 2026

**D03 completato, dodicesima voce su 18.** Simulatore operativo, contratti v4,
90 simulazioni native verificate, 30 gruppi seed e split 54/18/18.
8239 missioni e 1040241 snapshot rolling. Prossima voce: M01, non ancora iniziata.

- [Roadmap completa](docs/stato-roadmap.md)
- [Specifica unificata](docs/Specifica_Unificata_Logistica_Predittiva_v1.md)
- [Chiusura D03](reports/d03-closeout-20261014/Chiusura_D03.md)
- [Contratti e decisioni](docs/decisioni-nucleo-v1.md)
- [Dataset: distribuzione e riproduzione](data/d03/README.md)

I dati completi sono nel [ramo d03-dataset-v1](https://github.com/Zistax/digital-twin-military-logistics/tree/d03-dataset-v1),
con parti verificate e script di ricomposizione. Log, cache e diagnostica sono
versionati nello [snapshot locale](reports/runtime-snapshot-20261014/README.md).

Qualità verificata: 268 test e 16 sotto-test; copertura del nucleo 91,78%.
Per ripetere i controlli, installare le dipendenze runtime e
`requirements-quality.txt`, quindi eseguire:

```bash
python scripts/check_quality.py --report reports/quality-nuova-verifica
```

Le sezioni seguenti descrivono il prototipo storico. La nuova API/UI e i nuovi
modelli predittivi restano nelle fasi M01–U01 della roadmap.

---

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

## Etica & Privacy (senza PII)

Questo progetto e' pensato per lavorare con **dati sintetici** e/o dati
che non contengono **informazioni personali identificabili (PII)**.

Principi chiave:

- i log e i dataset usano ID pseudonimizzati (es. `session_id`, `convoy_id`),
- non vengono registrati nomi, cognomi, email, numeri di telefono, targhe reali, ecc.,
- i file di log seguono uno schema documentato (vedi `04 — Logging & Schema Dati`)
  e sono pensati per scopi di simulazione e analisi tecnica.

Per maggiori dettagli, vedi: `docs/etica_terminologia_licensing.md`.

## Licenza

Il core del progetto (cartella `src/` e file principali alla radice del repository)
e' rilasciato sotto licenza **Apache-2.0**. Vedi il file:

- `LICENSE`

La cartella `plugins/` e' pensata per contenere estensioni, connettori o integrazioni
che possono essere soggette a licenze diverse (incluse licenze proprietarie).
In tal caso, ogni plugin dovrebbe avere un proprio `README.md` con note di licensing.