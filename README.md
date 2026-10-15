# Digital twin logistico

## Stato del nuovo nucleo — 15 ottobre 2026

**R01 completata; R02 implementata e verificata offline.** Simulatore operativo, contratti v4,
90 simulazioni native verificate, 30 gruppi seed e split 54/18/18.
8239 missioni e 1040241 snapshot rolling. Baseline e previsione iniziale M01
confrontate sul training; calibrazione separata e astensione implementate.
Rolling, residuo, intervalli e servizio di aggiornamento M02 implementati;
intervalli molto larghi e censura esplicitati nel rapporto.
Test finale e registro M03 completati: candidato non ammesso alla promozione,
nessun modello attivo. API native e quattro viste locali collegate e verificate.
Pacchetto locale, installazione bloccata e verifica end-to-end disponibili.
R02 aggiunge accessi temporanei, isolamento e persistenza SQLite. Hosting e
pubblicazione restano sospesi per richiesta del proprietario.
Anche il container locale Linux amd64 è stato costruito e verificato.

- [Container R02: avvio e verifica locale](docs/container-r02.md)
- [Verifica del container R02](reports/r02-container-v1/Chiusura_Container.md)
- [Demo R02: avvio offline e limiti](docs/demo-r02.md)
- [Chiusura R02 nel perimetro offline](reports/r02-v1/Chiusura_R02.md)
- [Installazione del pacchetto locale R01](docs/pacchetto-locale-r01.md)
- [Chiusura R01](https://github.com/Zistax/digital-twin-military-logistics/blob/master/reports/r01-v1/Chiusura_R01.md)
- [Avvio API e quattro viste native](docs/api-ui-u01.md)
- [Chiusura U01 e validazione](reports/u01-v1/Chiusura_U01.md)
- [Roadmap completa](docs/stato-roadmap.md)
- [Specifica unificata](docs/Specifica_Unificata_Logistica_Predittiva_v1.md)
- [Chiusura M03: test, gate e registro](reports/m03-v1/Chiusura_M03.md)
- [Protocollo M03](docs/protocollo-m03-v1.md)
- [Chiusura M02 e comandi di riproduzione](reports/m02-v1/Chiusura_M02.md)
- [Protocollo M02](docs/protocollo-m02-v1.md)
- [Chiusura M01 e comandi di riproduzione](reports/m01-v1/Chiusura_M01.md)
- [Protocollo M01](docs/protocollo-m01-v1.md)
- [Chiusura D03](reports/d03-closeout-20261014/Chiusura_D03.md)
- [Contratti e decisioni](docs/decisioni-nucleo-v1.md)
- [Dataset: distribuzione e riproduzione](data/d03/README.md)

I dati completi sono nel [ramo d03-dataset-v1](https://github.com/Zistax/digital-twin-military-logistics/tree/d03-dataset-v1),
con parti verificate e script di ricomposizione. Log, cache e diagnostica sono
versionati nello [snapshot locale](reports/runtime-snapshot-20261014/README.md).

Qualità R02 su Windows: 365 test e 16 sotto-test; un test symlink saltato
per privilegio Windows mancante; copertura del nucleo 93.03%.
Per ripetere i controlli, installare le dipendenze runtime e
`requirements-quality.txt`, quindi eseguire:

```bash
python scripts/check_quality.py --report reports/quality-nuova-verifica
```

La dashboard attuale usa `/v1`: [avvio e limiti locali](docs/api-ui-u01.md).
Le sezioni seguenti documentano il prototipo storico ancora compatibile.

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

## UI Web nativa (Streamlit)

La dashboard ora usa le quattro viste U01 del nucleo logistico. Seguire la
[guida attuale](docs/api-ui-u01.md). Il vecchio rischio convoglio resta
accessibile attraverso gli endpoint storici.

### Soglia di rischio predefinita

Il sistema utilizza una **soglia di rischio predefinita**:

- `RISK_THRESHOLD_DEFAULT` (definita in `src/ml/risk_threshold.py`)

Questa soglia è stata scelta analizzando precision, recall e F1 nel notebook
`notebooks/evaluate_risk_model.ipynb`. I componenti storici CLI/API
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

- La UI nativa usa `/v1/sessions` e gli altri endpoint `/v1`, con URL base
  configurabile nella sidebar (default `http://127.0.0.1:8000`).

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
