# Fase 20 – Health check & logging operativo API (Parte 1, Giorni 1–3, Windows)

> **Obiettivo pratico (Parte 1)**  
> Aggiungere al progetto:
>
> - un endpoint **`GET /health`** per verificare rapidamente lo stato dell’API,
> - uno script **di health-check** da riga di comando,
> - un logging di base per le chiamate API in un file dedicato (`logs/api/api.log`).

L’idea è avere strumenti minimi ma concreti per capire “il sistema è su?”
e avere traccia di cosa sta succedendo in produzione (o nel tuo ambiente).


---

## Struttura Fase 20 – Parte 1

- **Giorno 1** – Endpoint `GET /health` in FastAPI
- **Giorno 2** – Script `check_api_health` (Python + `.bat`)
- **Giorno 3** – Logging operativo su file `logs/api/api.log`


---

## Giorno 1 – Endpoint `GET /health`

### Obiettivo del giorno
- Aggiungere a `src/api/app.py` un endpoint `/health` che ritorna:
  - stato (“ok” o “degraded”),
  - versione del modello (se disponibile),
  - un paio di info minime (timestamp, nome servizio).


---

### 1. Aprire `src\api\app.py` e aggiungere il modello `HealthResponse`

1. In **VS Code**, apri il file:

   - `src/api/app.py`

2. In cima al file, tra gli altri import, aggiungi:

```python
from datetime import datetime
from typing import Any

from src.ml.model_info import get_model_version
```

> `get_model_version` lo hai già usato in altri punti (es. `/optimize`);
> se l’import esiste già, non serve aggiungerlo di nuovo.

3. Vicino agli altri modelli Pydantic (es. `PredictRequest`, `OptimizeResponse`, ecc.),
   aggiungi il modello per la risposta di health:

```python
class HealthResponse(BaseModel):
    status: str
    version: str | None = None
    details: dict[str, Any] | None = None
```

> Assicurati che `BaseModel` sia già importato da `pydantic` (lo è dalle fasi precedenti).

**Checklist**
- [ ] `src/api/app.py` importa `datetime`, `Any` e `get_model_version`
- [ ] Esiste la classe `HealthResponse`


---

### 2. Aggiungere l’endpoint `GET /health`

1. Sempre in `src/api/app.py`, sotto la definizione dell’app FastAPI e vicino agli altri
   endpoint (`/predict`, `/simulate`, ecc.), aggiungi:

```python
@app.get("/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    """Endpoint di health-check dell'API.

    Ritorna uno stato semplice e, se possibile, la versione del modello.
    """
    try:
        model_version = get_model_version("models/risk_model.pkl")
    except Exception:
        model_version = None

    status = "ok"
    if model_version is None:
        # Non riusciamo a leggere la versione del modello, ma l'API risponde
        status = "degraded"

    return HealthResponse(
        status=status,
        version=model_version,
        details={
            "service": "risk_api",
            "time_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
```

2. Salva il file.

**Checklist**
- [ ] Esiste l’endpoint `@app.get("/health", ...)` che ritorna `HealthResponse`


---

### 3. Prova dell’endpoint `/health`

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
uvicorn src.api.app:app --reload
```

2. Apri il browser su:

- `http://127.0.0.1:8000/health`

Dovresti vedere una risposta JSON simile a:

```json
{
  "status": "ok",
  "version": "risk_model_v1",
  "details": {
    "service": "risk_api",
    "time_utc": "2025-11-16T12:34:56Z"
  }
}
```

> Se la `version` è `null`/`None` ma tutto il resto funziona, è comunque accettabile
> (lo stato sarà `degraded`).

3. Vai anche in Swagger UI:

- `http://127.0.0.1:8000/docs`

e controlla che l’endpoint `GET /health` compaia nel gruppo tag `ops`.

**Checklist (fine Giorno 1)**
- [ ] `/health` risponde con HTTP 200
- [ ] Swagger mostra l’endpoint `GET /health`
- [ ] La risposta include almeno `status`, `version` e `details.time_utc`


---

## Giorno 2 – Script di health-check: `check_api_health`

### Obiettivo del giorno
- Creare uno script **Python** che chiama `/health` e stampa un risultato chiaro,
- aggiungere un piccolo **`.bat`** per lanciarlo facilmente su Windows.


---

### 1. Creare il package `src\tools`

1. In **VS Code**, nella cartella `src`, crea la cartella:

   - `tools`

2. Dentro `src\tools`, crea un file vuoto:

   - `__init__.py`

Puoi farlo da VS Code o da terminale:

```bash
mkdir src\tools
type NUL > src\tools\__init__.py
```

**Checklist**
- [ ] Esiste `src\tools`
- [ ] Esiste `src\tools\__init__.py`


---

### 2. Creare `src\tools\check_api_health.py`

1. Sempre in `src\tools`, crea il file:

   - `check_api_health.py`

2. Inserisci il codice seguente:

```python
from __future__ import annotations

import sys
from typing import Any, Dict

import requests


DEFAULT_API_URL = "http://127.0.0.1:8000/health"


def check_api_health(url: str = DEFAULT_API_URL) -> int:
    """Chiama l'endpoint /health e stampa un breve riepilogo.

    Ritorna un exit code:
    - 0 se status='ok'
    - 1 altrimenti (degraded, errore HTTP, eccezioni)
    """
    try:
        resp = requests.get(url, timeout=5)
    except requests.RequestException as exc:  # noqa: PERF203
        print(f"[ERRORE] Impossibile contattare l'API: {exc}")
        return 1

    if resp.status_code != 200:
        print(f"[ERRORE] /health ha risposto con status code {resp.status_code}")
        return 1

    try:
        data: Dict[str, Any] = resp.json()
    except ValueError:
        print("[ERRORE] La risposta /health non e' JSON valido.")
        return 1

    status = data.get("status", "unknown")
    version = data.get("version", None)
    details = data.get("details", {}) or {}

    print("=== API Health Check ===")
    print(f"URL:     {url}")
    print(f"Status:  {status}")
    print(f"Version: {version}")
    if details:
        print("Dettagli:")
        for k, v in details.items():
            print(f"  - {k}: {v}")

    if status != "ok":
        return 1

    return 0


def main() -> None:
    url = DEFAULT_API_URL
    if len(sys.argv) > 1:
        url = sys.argv[1]

    exit_code = check_api_health(url)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

3. Salva il file.

> Questo script torna **exit code 0** se tutto è ok, altrimenti 1.  
> In futuro potrai usarlo anche dentro script `.bat` o in eventuali scheduler.


**Checklist**
- [ ] Esiste `src/tools/check_api_health.py` con funzione `check_api_health` e `main()`


---

### 3. Assicurarsi che `requests` sia nei requirements

1. Apri `requirements.txt`.
2. Controlla che ci sia la libreria `requests` (probabilmente presente già per la UI).  
   In caso contrario, aggiungi una riga:

```txt
requests
```

3. Salva il file.

4. Nel terminale (con `.venv` attivo), reinstalla le dipendenze (se necessario):

```bash
pip install -r requirements.txt
```

**Checklist**
- [ ] `requests` è presente in `requirements.txt`
- [ ] Le dipendenze sono installate senza errori


---

### 4. Testare lo script `check_api_health` da Python

1. Assicurati che l’API sia in esecuzione:

```bash
uvicorn src.api.app:app --reload
```

2. In un altro terminale (sempre nella root del progetto, con `.venv` attivo):

```bash
python -m src.tools.check_api_health
```

Dovresti vedere un output simile a:

```text
=== API Health Check ===
URL:     http://127.0.0.1:8000/health
Status:  ok
Version: risk_model_v1
Dettagli:
  - service: risk_api
  - time_utc: 2025-11-16T12:45:00Z
```

**Checklist**
- [ ] `python -m src.tools.check_api_health` funziona e stampa lo stato API


---

### 5. (Opzionale) Creare un `.bat` di comodo: `check_api_health.bat`

1. Nella root del progetto, crea un file:

   - `check_api_health.bat`

2. Inserisci:

```bat
@echo off
REM Attiva l'ambiente virtuale (adatta il percorso se diverso)
call .venv\Scripts\activate

REM Esegue lo script di health-check
python -m src.tools.check_api_health %*
```

3. Salva il file.

4. Prova a lanciarlo da **cmd** (nella root del progetto):

```bash
check_api_health.bat
```

**Checklist (fine Giorno 2)**
- [ ] Esiste `check_api_health.bat` (opzionale ma consigliato)
- [ ] Puoi verificare lo stato dell’API con un singolo comando


---

## Giorno 3 – Logging operativo API su file

### Obiettivo del giorno
- Abilitare un logging di base per l’API:
  - file di log in `logs/api/api.log`,
  - righe di log ogni volta che vengono chiamati `/health` e gli endpoint principali.


---

### 1. Creare la cartella `logs/api`

1. In Esplora File o VS Code, crea le cartelle:

   - `logs`
   - `logs/api`

Oppure da terminale, nella root del progetto:

```bash
mkdir logs
mkdir logs\api
```

**Checklist**
- [ ] Esiste `logs/api`


---

### 2. Creare `src\api\logging_setup.py`

1. In **VS Code**, dentro `src/api`, crea il file:

   - `logging_setup.py`

2. Inserisci il seguente codice:

```python
from __future__ import annotations

import logging
from pathlib import Path


LOG_DIR = Path("logs") / "api"
LOG_FILE = LOG_DIR / "api.log"


def setup_api_logger() -> logging.Logger:
    """Configura un logger di base per l'API.

    - scrive su logs/api/api.log
    - logga anche su console
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("api")
    logger.setLevel(logging.INFO)

    # Evitiamo di aggiungere piu' handler se setup_api_logger viene chiamato piu' volte
    if not logger.handlers:
        # File handler
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    return logger
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/api/logging_setup.py` con `setup_api_logger()`


---

### 3. Usare il logger in `app.py`

1. Apri `src/api/app.py`.
2. In cima, tra gli import, aggiungi:

```python
from src.api.logging_setup import setup_api_logger
```

3. Subito dopo aver creato l’oggetto `app = FastAPI(...)`, aggiungi:

```python
logger = setup_api_logger()
```

> In questo modo il logger viene configurato all’avvio dell’app.

4. All’interno dell’endpoint `/health`, prima del `return`, aggiungi una riga di log:

```python
    logger.info("Health check chiamato: status=%s, version=%s", status, model_version)
```

5. Se vuoi (consigliato), aggiungi log anche negli endpoint principali.  
   Esempio su `/predict` (adatta al tuo codice reale):

```python
@app.post("/predict", response_model=PredictResponse, tags=["ml"])
def predict(request: PredictRequest) -> PredictResponse:
    logger.info("POST /predict chiamato")

    # ... codice esistente ...

    return response
```

Ripeti con una riga simile per `/simulate`, `/optimize`, ecc.

6. Salva `app.py`.

**Checklist**
- [ ] `app.py` importa `setup_api_logger` e crea `logger = setup_api_logger()`
- [ ] `/health` scrive una riga di log con status/version
- [ ] Almeno un endpoint principale (es. `/predict`) scrive una riga di log


---

### 4. Verifica del logging

1. Nel terminale, avvia di nuovo l’API (se non è già attiva):

```bash
uvicorn src.api.app:app --reload
```

2. Fai un paio di richieste:

- apri `http://127.0.0.1:8000/health` nel browser,
- se vuoi, manda una richiesta `/predict` tramite Swagger o `curl`/UI.

3. Apri il file `logs/api/api.log` con VS Code.

Dovresti vedere righe simili a:

```text
2025-11-16 13:00:12,345 [INFO] api - Health check chiamato: status=ok, version=risk_model_v1
2025-11-16 13:02:01,123 [INFO] api - POST /predict chiamato
```

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] Il file `logs/api/api.log` viene creato automaticamente
- [ ] Ogni chiamata a `/health` aggiunge una riga di log
- [ ] Almeno un endpoint business (es. `/predict`) logga le chiamate


---

Con questa Parte 1 hai:

- un endpoint `/health` per controllare velocemente lo stato dell’API,
- uno script `check_api_health` (anche `.bat`) per fare health-check da riga di comando,
- logging operativo di base su file, utile per debug e per capire cosa accade in runtime.

Nella **Parte 2** (`fase20_2.md`) documenterai meglio l’operatività (runbook) e aggiungerai
un piccolo “check ops” che combina health-check e verifiche base.
