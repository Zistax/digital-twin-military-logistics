# Fase 22 – Sicurezza base API & accesso (Parte 2, Giorni 4–6, Windows)

> **Obiettivo pratico (Parte 2)**  
> Rafforzare leggermente la sicurezza e documentarla meglio:
>
> - configurare CORS in modo esplicito,
> - aggiungere un semplice rate limit in memoria per gli endpoint costosi,
> - loggare i tentativi di accesso falliti,
> - scrivere una breve nota di sicurezza (`docs/security_notes.md`).


---

## Struttura Fase 22 – Parte 2

- **Giorno 4** – Configurazione CORS esplicita
- **Giorno 5** – Semplice rate limit in memoria + log tentativi falliti
- **Giorno 6** – `docs/security_notes.md` + aggiornamento README + commit finale


---

## Giorno 4 – CORS esplicito

### Obiettivo del giorno
- Configurare CORS su FastAPI in modo chiaro, anche se lo usi solo in locale,
- evitare di lasciare il default troppo permissivo senza saperlo.


---

### 1. Aggiungere configurazione CORS in `app.py`

1. Apri `src/api/app.py`.
2. In cima, tra gli import, aggiungi:

```python
from fastapi.middleware.cors import CORSMiddleware
```

3. Dopo aver creato l’oggetto `app = FastAPI(...)` e configurato il logger/middleware,
   aggiungi:

```python
origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:8501",      # Streamlit default
    "http://127.0.0.1:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

4. Salva il file.

**Checklist**
- [ ] `CORSMiddleware` importato
- [ ] `app.add_middleware(CORSMiddleware, ...)` configurato con origins ragionevoli


---

### 2. Test rapido CORS (manuale)

1. Avvia l’API:

```bash
uvicorn src.api.app:app --reload
```

2. Apri la UI Streamlit (dashboard) e verifica che le richieste verso l’API
   non diano errori CORS in console (puoi guardare gli strumenti sviluppatore del browser).

> Se non vedi errori CORS e la UI continua a funzionare, la configurazione va bene.

**Checklist (fine Giorno 4)**
- [ ] CORS configurato in maniera esplicita
- [ ] La UI continua a funzionare senza errori CORS


---

## Giorno 5 – Rate limit base & log tentativi falliti

### Obiettivo del giorno
- Aggiungere un **rate limit molto semplice in memoria** per endpoint costosi
  (es. `/predict`, `/simulate`, `/optimize`),
- assicurarsi che i tentativi di accesso con API key sbagliata vengano loggati.


---

### 1. Aggiungere log per accessi falliti in `security_dep.py`

1. Apri `src/api/security_dep.py`.
2. In cima, aggiungi:

```python
import logging

logger = logging.getLogger("api")
```

3. Dentro `verify_api_key`, prima di sollevare `HTTPException`, aggiungi:

```python
    if not x_api_key or x_api_key != server_key:
        logger.warning("Accesso negato: API key non valida o mancante")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
```

(in pratica sostituisci il blocco precedente con quello che include il log).

4. Salva il file.

**Checklist**
- [ ] I tentativi di accesso con chiave errata vengono loggati nel file `api.log`


---

### 2. Semplice rate limit in memoria (per IP + path)

> Nota: non è un rate limiter “da produzione”, ma basta a farti capire come funziona.

1. Crea (se non esiste) il file `src/api/rate_limit.py`.

2. Inserisci:

```python
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import HTTPException, Request, status


# Struttura in memoria: (ip, path) -> lista di timestamp delle richieste
_requests_history: Dict[Tuple[str, str], list[float]] = defaultdict(list)


def rate_limit(
    request: Request,
    max_requests: int = 30,
    window_seconds: int = 60,
) -> None:
    """Semplice rate limit in memoria per IP+path.

    - max_requests: numero max di richieste per finestra temporale
    - window_seconds: ampiezza finestra in secondi

    Se il client supera la soglia, viene sollevata 429 Too Many Requests.
    """
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    now = time.time()

    key = (client_ip, path)
    history = _requests_history[key]

    # Manteniamo solo le richieste nella finestra corrente
    cutoff = now - window_seconds
    history = [ts for ts in history if ts >= cutoff]
    history.append(now)
    _requests_history[key] = history

    if len(history) > max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, please slow down.",
        )
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/api/rate_limit.py` con funzione `rate_limit`


---

### 3. Applicare il rate limit a endpoint costosi

1. Apri `src/api/app.py`.
2. Aggiungi tra gli import in cima:

```python
from fastapi import Request
from src.api.rate_limit import rate_limit
```

> `Request` potrebbe essere già importato in `app.py` per altri usi; se è così, non duplicare.

3. Modifica la firma degli endpoint che vuoi proteggere (es. `/predict`).  
   Esempio:

```python
@app.post("/predict", response_model=PredictResponse, tags=["ml"])
def predict(
    request: PredictRequest,
    _: None = RequireAPIKey,
) -> PredictResponse:
    ...
```

Diventa:

```python
@app.post("/predict", response_model=PredictResponse, tags=["ml"])
def predict(
    request: PredictRequest,
    http_request: Request,
    _: None = RequireAPIKey,
) -> PredictResponse:
    rate_limit(http_request, max_requests=60, window_seconds=60)
    ...
```

> Tradotto: massimo 60 richieste al minuto per IP per l’endpoint `/predict`.

4. Ripeti per altri endpoint costosi, per esempio:

- `/simulate`
- `/optimize`

(adattando eventualmente `max_requests` e `window_seconds` in base al tipo di chiamata).

5. Salva `app.py`.

**Checklist**
- [ ] Gli endpoint costosi chiamano `rate_limit(http_request, ...)` all’inizio
- [ ] Il parametro `http_request: Request` è presente nelle firme


---

### 4. Test manuale del rate limit

1. Avvia l’API:

```bash
uvicorn src.api.app:app --reload
```

2. In un terminale, usa un piccolo script o anche `load_test_api` puntato su `/predict`
   con la chiave corretta (potresti dover adattare il body).  
   Oppure lancia molte richieste in poco tempo da Swagger.

3. Quando superi la soglia (es. oltre 60 richieste al minuto), dovresti ricevere:

```json
{
  "detail": "Too many requests, please slow down."
}
```

con status code **429**.

**Checklist (fine Giorno 5)**
- [ ] I tentativi oltre soglia restituiscono 429
- [ ] Nel log vedi gli accessi (e, se vuoi, puoi aggiungere una riga di log in `rate_limit`)  


---

## Giorno 6 – Note di sicurezza & aggiornamento README


### Obiettivo del giorno
- Scrivere un breve documento con le **note di sicurezza** del progetto,
- aggiornare il `README.md` per puntare a questo documento,
- fare il commit di chiusura della Fase 22.


---

### 1. Creare `docs\security_notes.md`

1. In **VS Code**, nella cartella `docs`, crea il file:

   - `security_notes.md`

2. Inserisci contenuti simili (puoi adattare la forma ma lascia i concetti):

```markdown
# Note di sicurezza – Digital Twin logistico

Queste note riassumono il livello di sicurezza implementato nel progetto e i limiti
da tenere presenti (non e' un hardening di produzione, ma un set di buone pratiche base).

## 1. API key

- Gli endpoint principali (`/predict`, `/simulate`, `/optimize`, ...) sono protetti da
  una API key semplice, passata tramite header `X-API-Key`.
- La chiave viene letta da:
  - variabile d'ambiente `API_KEY_RISK`
  - in sviluppo, facoltativamente da `conf/ops/api_keys.yml`
- L'endpoint `/health` resta pubblico per permettere monitoraggio esterno.

Limitazioni:

- la API key e' condivisa (non per-utente) e non e' ruotata automaticamente;
- non e' presente un meccanismo di autenticazione forte (OAuth2, JWT, ecc.).

## 2. Rate limiting

- Alcuni endpoint costosi (es. `/predict`, `/simulate`, `/optimize`) usano un
  semplice rate limit in memoria (per IP+path, con finestra di 60 secondi).
- Questo protegge da abuso involontario, ma:
  - non e' distribuito (vale solo per il singolo processo),
  - non resiste ad attacchi intenzionali distribuiti.

## 3. CORS

- CORS e' configurato esplicitamente per origin locali (localhost, 127.0.0.1, Streamlit).
- In caso di deploy in un altro dominio, aggiornare `origins` in `src/api/app.py`.

## 4. Log

- I tentativi di accesso con API key errata vengono loggati in `logs/api/api.log`.
- I log non devono contenere chiavi o dati sensibili (controllare eventuali future estensioni).

## 5. Raccomandazioni per un futuro hardening

Per un contesto produttivo sarebbe opportuno:

- usare un identity provider e token con scadenza (es. OAuth2/OIDC);
- gestire i segreti con un secret manager (Azure Key Vault, AWS Secrets Manager, ...);
- introdurre rate limiting centralizzato o gateway API;
- aggiungere audit log strutturati (chi ha fatto cosa e quando);
- gestire la cifratura a riposo dei dati sensibili e dei backup.
```

3. Salva il file.

**Checklist**
- [ ] Esiste `docs/security_notes.md` con le note di sicurezza


---

### 2. Aggiornare il README per puntare alle note di sicurezza

1. Apri `README.md`.
2. Nella sezione “Sicurezza API (API key)” o subito sotto, aggiungi una riga tipo:

```markdown
Per una panoramica dei meccanismi di sicurezza implementati e dei relativi limiti,
vedi anche:

- `docs/security_notes.md`
```

3. Salva il file.

**Checklist**
- [ ] Il README linka `docs/security_notes.md`


---

### 3. Giro finale + commit Fase 22

1. Esegui almeno una volta i test:

```bash
pytest
```

2. Esegui un piccolo giro manuale:

- `/health` senza API key,
- `/predict` con API key corretta,
- `/predict` con chiave sbagliata (deve dare 401),
- eventuale superamento del rate limit (429).

3. Se tutto ok, crea il commit:

```bash
git add src/config/security.py conf/ops/api_keys.example.yml src/api/security_dep.py src/api/rate_limit.py src/api/app.py docs/security_notes.md tests/test_api_security.py README.md
git commit -m "Fase 22: sicurezza base API (API key, CORS, rate limit)"
git push
```

**Checklist (fine Giorno 6 – fine Fase 22)**
- [ ] API key configurata e funzionante
- [ ] Endpoint sensibili protetti e testati
- [ ] CORS esplicito e rate limit base configurato
- [ ] Note di sicurezza scritte e collegate dal README


---

Con la Fase 22 hai portato il progetto a un livello migliore di **igiene di sicurezza**:

- accesso agli endpoint non più completamente aperto,
- qualche protezione contro abusi e uso improprio,
- documentazione chiara su cosa c’è e cosa **non** c’è a livello di sicurezza,
  così da sapere dove intervenire se un domani vorrai renderlo “prod-ready”.
