# Fase 22 – Sicurezza base API & accesso (Parte 1, Giorni 1–3, Windows)

> **Obiettivo pratico (Parte 1)**  
> Aggiungere un primo livello di **sicurezza applicativa** alle API:
>
> - gestione di una **API key** lato server,
> - protezione degli endpoint sensibili (`/predict`, `/simulate`, `/optimize`, ecc.),
> - test automatici per verificare che la protezione funzioni,
> - documentazione minima.

L’idea è avere qualcosa di semplice ma concreto:  
non è sicurezza “enterprise”, ma è già molto meglio di un’API completamente aperta.


---

## Struttura Fase 22 – Parte 1

- **Giorno 1** – Configurazione della API key (file di config + variabile d’ambiente)
- **Giorno 2** – Dependency FastAPI per validare la API key e protezione endpoint
- **Giorno 3** – Test automatici di sicurezza + aggiornamento README


---

## Giorno 1 – Configurazione API key (config + env)

### Obiettivo del giorno
- Definire dove è configurata la API key,
- evitare di scriverla hard-coded nel codice,
- preparare un meccanismo semplice per usarla in sviluppo e in “pseudo-prod”.


---

### 1. Scegliere la strategia: env + file di esempio

Useremo:
- una variabile d’ambiente **`API_KEY_RISK`** che contiene la chiave reale,
- un file di esempio `conf/ops/api_keys.example.yml` per documentare il formato,
- un fallback opzionale in dev (`conf/ops/api_keys.yml`) se vuoi.

> In sistemi reali si userebbero secret manager, ma per questo progetto è sufficiente
> env + file di esempio.

**Checklist**
- [ ] Deciso di usare `API_KEY_RISK` per la chiave di accesso


---

### 2. Creare file di esempio `conf\ops\api_keys.example.yml`

1. In **VS Code**, nella cartella `conf/ops` (esiste dalla Fase 21), crea il file:

   - `api_keys.example.yml`

2. Inserisci:

```yaml
# Esempio di file per configurare API key lato server.
# NON usare questo file in produzione con chiavi reali
# (usare invece variabili d'ambiente o secret manager).

risk_api:
  # API key di esempio (per sviluppo)
  # In produzione usare la variabile d'ambiente API_KEY_RISK
  key: "CAMBIA_QUESTA_CHIAVE"
```

3. Salva il file.

> Se vuoi, puoi fare una copia chiamata `api_keys.yml` da usare **solo in locale**
> (non committarla o aggiungila a `.gitignore`).

**Checklist**
- [ ] Esiste `conf/ops/api_keys.example.yml`


---

### 3. (Opzionale) Aggiungere `conf/ops/api_keys.yml` a `.gitignore`

Se decidi di usare un file locale con chiavi “reali”, è importante non committarlo.

1. Apri `.gitignore` nella root del progetto.
2. Aggiungi (se non presente):

```txt
conf/ops/api_keys.yml
```

3. Salva il file.

**Checklist**
- [ ] `.gitignore` contiene `conf/ops/api_keys.yml` (se lo vuoi usare in locale)


---

### 4. Creare modulo `src\config\security.py`

1. In **VS Code**, crea la cartella `src/config` se non esiste già (molto probabile che ci sia già; in caso, salta questo passo).  
   Comunque assicurati che esista `src/config/__init__.py` (puoi creare un file vuoto).

Da terminale (se serve):

```bash
mkdir src\config
type NUL > src\config\__init__.py
```

2. Crea il file:

   - `src/config/security.py`

3. Inserisci il codice seguente:

```python
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml


API_KEYS_FILE = Path("conf") / "ops" / "api_keys.yml"
API_KEYS_EXAMPLE_FILE = Path("conf") / "ops" / "api_keys.example.yml"


def load_risk_api_key() -> Optional[str]:
    """Carica la API key per la risk API.

    Priorita':
    1. variabile d'ambiente API_KEY_RISK
    2. file conf/ops/api_keys.yml se esiste
    3. se non trovato, None (API senza protezione forte)
    """
    # 1) Env
    env_key = os.getenv("API_KEY_RISK")
    if env_key:
        return env_key

    # 2) File locale (non committato, solo dev)
    if API_KEYS_FILE.exists():
        with API_KEYS_FILE.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        risk_cfg = data.get("risk_api", {})
        file_key = risk_cfg.get("key")
        if file_key:
            return str(file_key)

    # 3) Nessuna chiave trovata
    return None
```

4. Salva il file.

**Checklist (fine Giorno 1)**
- [ ] `src/config/security.py` esiste con `load_risk_api_key`
- [ ] Esiste `conf/ops/api_keys.example.yml`
- [ ] (Opzionale) `.gitignore` ignora `conf/ops/api_keys.yml`


---

## Giorno 2 – Dependency FastAPI per validare la API key

### Obiettivo del giorno
- Scrivere una dependency FastAPI che:
  - legge la API key inviata dal client (header `X-API-Key`),
  - la confronta con quella caricata da `load_risk_api_key`,
  - se non coincide, restituisce **401 Unauthorized**,
- applicarla agli endpoint sensibili (`/predict`, `/simulate`, `/optimize`, …).


---

### 1. Creare `src\api\security_dep.py`

1. In **VS Code**, nella cartella `src/api`, crea il file:

   - `security_dep.py`

2. Inserisci:

```python
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from src.config.security import load_risk_api_key


async def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Dependency che verifica la API key passata nell'header X-API-Key.

    - Se non e' configurata nessuna chiave lato server, non fa nulla (modalita' 'open').
    - Se e' configurata una chiave, la confronta con X-API-Key e, in caso di mismatch,
      solleva una HTTP 401.
    """
    server_key = load_risk_api_key()

    # Se nessuna chiave configurata, non blocchiamo (utile in dev).
    if not server_key:
        return

    if not x_api_key or x_api_key != server_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


RequireAPIKey = Depends(verify_api_key)
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/api/security_dep.py` con `verify_api_key` e `RequireAPIKey`


---

### 2. Proteggere gli endpoint sensibili in `app.py`

1. Apri `src/api/app.py`.
2. In cima al file, tra gli import, aggiungi:

```python
from fastapi import Depends
from src.api.security_dep import RequireAPIKey
```

> `Depends` potrebbe essere già importato; in quel caso non duplicare.

3. Cerca la definizione degli endpoint sensibili, ad esempio:

```python
@app.post("/predict", response_model=PredictResponse, tags=["ml"])
def predict(request: PredictRequest) -> PredictResponse:
    ...
```

e modificala così:

```python
@app.post("/predict", response_model=PredictResponse, tags=["ml"])
def predict(
    request: PredictRequest,
    _: None = RequireAPIKey,
) -> PredictResponse:
    ...
```

Stesso discorso per gli altri endpoint che vuoi proteggere, per esempio:

- `/simulate`
- `/optimize`
- eventuali altri endpoint di business.

**Non** applicare la dependency a `/health` (deve restare accessibile liberamente).

4. Salva `app.py`.

**Checklist**
- [ ] Gli endpoint sensibili accettano un argomento `_: None = RequireAPIKey`
- [ ] `/health` resta senza dependency di sicurezza


---

### 3. Test manuale via curl / Swagger

1. Imposta una API key per i test, ad esempio nel tuo terminale PowerShell:

```bash
setx API_KEY_RISK "MIA_CHIAVE_TEST"
```

> Poi **chiudi e riapri** il terminale per far rileggere le variabili.

2. Attiva `.venv` e lancia l’API:

```bash
call .venv\Scripts\activate
uvicorn src.api.app:app --reload
```

3. Test senza chiave:

   - vai su Swagger: `http://127.0.0.1:8000/docs`
   - prova a chiamare `/predict` senza header `X-API-Key`

   Dovresti ottenere **401 Unauthorized** con `{"detail":"Invalid or missing API key"}`.

4. Test con chiave:

   - sempre da Swagger, aggiungi l’header `X-API-Key` con valore `MIA_CHIAVE_TEST`
     (c’è una sezione “Headers” da aggiungere nella request).
   - riprova `/predict`: ora deve funzionare come prima.

5. `/health` deve continuare a rispondere **senza** richiedere nessun header.

**Checklist (fine Giorno 2)**
- [ ] `/predict` (e altri endpoint protetti) rispondono 401 senza `X-API-Key`
- [ ] Con `X-API-Key` corretta gli endpoint funzionano
- [ ] `/health` risponde sempre (nessuna chiave richiesta)


---

## Giorno 3 – Test automatici + README


### Obiettivo del giorno
- Aggiungere test automatici per verificare il corretto comportamento,
- aggiornare il `README.md` con una sezione “Sicurezza API (API key)”.


---

### 1. Test automatici per la API key

1. In **VS Code**, nella cartella `tests`, crea il file:

   - `test_api_security.py`

2. Inserisci:

```python
import os

import pytest
from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_api_key_env(monkeypatch):
    # Imposta una API key fissa per i test
    monkeypatch.setenv("API_KEY_RISK", "TEST_KEY")
    yield
    # (monkeypatch ripristina automaticamente alla fine)


def test_predict_requires_api_key():
    response = client.post("/predict", json={"convoy_id": "C1", "timestep": 0})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_predict_with_valid_api_key():
    headers = {"X-API-Key": "TEST_KEY"}
    response = client.post("/predict", json={"convoy_id": "C1", "timestep": 0}, headers=headers)
    # Lo status code dipende dalla logica del tuo endpoint; qui ci aspettiamo 200 se tutto e' ok
    assert response.status_code == 200


def test_health_does_not_require_api_key():
    # /health deve essere accessibile anche senza chiave
    response = client.get("/health")
    assert response.status_code == 200
```

> Se il tuo `PredictRequest` ha un payload diverso, adatta il JSON di esempio.

3. Salva il file.

**Checklist**
- [ ] Esiste `tests/test_api_security.py` con test per accesso con/senza chiave


---

### 2. Eseguire i test

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest tests/test_api_security.py
```

Se ok, puoi lanciare l’intera suite:

```bash
pytest
```

**Checklist**
- [ ] I test di sicurezza passano
- [ ] I test precedenti non risultano rotti


---

### 3. Aggiornare il README con sezione “Sicurezza API (API key)”

1. Apri `README.md`.
2. Aggiungi una sezione simile:

```markdown
## Sicurezza API (API key)

Gli endpoint principali dell'API (es. `/predict`, `/simulate`, `/optimize`) sono
protetti da una **API key** semplice, basata su header HTTP `X-API-Key`.

Configurazione lato server:

- variabile d'ambiente: `API_KEY_RISK`
- opzionale file locale (solo in sviluppo): `conf/ops/api_keys.yml`
  (formato documentato in `conf/ops/api_keys.example.yml`)

Esempio di chiamata con `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/predict" ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: MIA_CHIAVE_TEST" ^
  -d "{\"convoy_id\": \"C1\", \"timestep\": 0}"
```

L'endpoint `/health` resta volutamente **non protetto**, in modo da poter essere
usato da strumenti di monitoraggio esterni senza bisogno di credenziali.
```

3. Salva il file.

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] Sezione sicurezza API aggiunta nel README
- [ ] I test di sicurezza passano
- [ ] Gli endpoint sono effettivamente protetti da API key (tranne `/health`)


---

Con la Parte 1 della Fase 22 hai introdotto una **protezione base** sulle tue API:

- hai una API key configurabile via env/file,
- gli endpoint sensibili non sono più aperti,
- hai test che ti garantiscono di non rompere questa logica in futuro.

Nella **Parte 2** aggiungerai qualche hardening leggero (CORS, rate limit base,
log di sicurezza) e un breve documento di “security notes”.
