# Fase 23 – Etica, Terminologia & Logging governance (Parte 1, Giorni 1–3, Windows)

> **Obiettivo pratico (Parte 1)**  
> Portare nel codice alcune scelte di **etica / governance** descritte nel documento
> `12-etica-terminologia-licensing.md`:
>
> - evitare PII nei log (sanitizzazione base),
> - introdurre un mapping di **terminologia neutra** per la UI,
> - aggiungere un **audit log** delle decisioni operatore vs suggerimenti modello/RL,
> - preparare i campi per future analisi di governance.

Non è “compliance GDPR completa”, ma è un primo passo concreto in quella direzione.


---

## Struttura Fase 23 – Parte 1

- **Giorno 1** – Sanitizzazione log (no PII) + linea guida per ID
- **Giorno 2** – Config terminologia neutra multi-tenant
- **Giorno 3** – Audit log decisioni operatore vs modello/RL


---

## Giorno 1 – Sanitizzazione log & no PII

### Obiettivo del giorno
- Verificare che i log non contengano dati personali,
- introdurre una piccola funzione di “sanitizzazione” per messaggi log,
- definire una convenzione per gli ID nei log.


---

### 1. Definire una funzione di sanitizzazione log

1. In **VS Code**, dentro `src/api`, crea il file:

   - `pii_sanitizer.py`

2. Inserisci il seguente codice:

```python
from __future__ import annotations

import re
from typing import Any, Dict


# Pattern molto basici per evitare di loggare PII ovvie.
# NON sostituisce una vera analisi legale/GDPR, ma e' un primo filtro.
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+")
PHONE_PATTERN = re.compile(r"\b\+?[0-9][0-9\- ]{5,}[0-9]\b")


def sanitize_text(text: str) -> str:
    """Rimuove pattern base di PII da una stringa (email, telefoni)."""
    text = EMAIL_PATTERN.sub("[EMAIL]", text)
    text = PHONE_PATTERN.sub("[PHONE]", text)
    return text


def sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ritorna una copia del payload con i campi sospetti mascherati.

    Per ora applichiamo `sanitize_text` a tutti i valori stringa.
    """
    clean: Dict[str, Any] = {}

    for k, v in payload.items():
        if isinstance(v, str):
            clean[k] = sanitize_text(v)
        else:
            clean[k] = v

    return clean
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/api/pii_sanitizer.py` con `sanitize_text` e `sanitize_payload`


---

### 2. Usare la sanitizzazione nei log API principali

1. Apri `src/api/app.py`.
2. Negli endpoint dove logghi direttamente il request body (se lo fai), evita di loggare
   il payload completo non sanitizzato.  
   Se vuoi loggare qualche campo, usa `sanitize_payload`.

   Esempio generico per `/predict` (adatta al tuo codice reale):

```python
from src.api.pii_sanitizer import sanitize_payload
```

Poi nella funzione:

```python
@app.post("/predict", response_model=PredictResponse, tags=["ml"])
def predict(
    request: PredictRequest,
    http_request: Request,
    _: None = RequireAPIKey,
) -> PredictResponse:
    rate_limit(http_request, max_requests=60, window_seconds=60)

    payload_dict = sanitize_payload(request.dict())
    logger.info("POST /predict payload_sanitized=%s", payload_dict)

    # ... resto della logica ...
```

3. Se in altri punti del codice usi `logger.info` con payload utente, applica lo stesso
   approccio (meglio loggare meno, ma mai PII).

4. Salva `app.py`.

**Checklist**
- [ ] I log non riportano più payload raw senza sanitizzazione
- [ ] `sanitize_payload` viene usato dove serve


---

### 3. Linea guida per ID non PII

> Non è codice, ma una **regola di progetto**.

Nel tuo modo di usare l’app:

- usa ID **pseudonimi** (es. `convoy-001`, `unit_023`, `mission_2025_11_16_A`) invece di nomi reali,
- non inserire mai nei dataset/log:
  - nomi e cognomi,
  - indirizzi email,
  - numeri di telefono,
  - coordinate precise di persone (il progetto è comunque su mappa sintetica 100×100 km).

Puoi annotare questa regola nel `README.md` (vedi Giorno 3).

**Checklist (fine Giorno 1)**
- [ ] È presente una funzione di sanitizzazione PII (anche se semplice)
- [ ] I log non stampano più payload grezzi non filtrati


---

## Giorno 2 – Config terminologia neutra multi‑tenant

### Obiettivo del giorno
- Introdurre un file di configurazione con la terminologia “neutra”,
- fornire mapping per alcuni termini base (es. `attack → threat_event`),
- preparare una funzione da usare nella UI per mostrare termini per-tenant.


---

### 1. Creare il file `conf\ops\terminology.yml`

1. In **VS Code**, nella cartella `conf/ops`, crea il file:

   - `terminology.yml`

2. Inserisci una struttura base, ad esempio:

```yaml
default:
  attack: "threat_event"
  breakdown: "mech_failure"
  convoy: "convoy"
  route: "route"

tenant_alpha:
  attack: "incident"
  breakdown: "vehicle_issue"
  convoy: "mission"
  route: "corridor"
```

3. Salva il file.

> Puoi modificare/nominare i tenant come preferisci; l’importante è avere un “default”.

**Checklist**
- [ ] Esiste `conf/ops/terminology.yml` con almeno la sezione `default`


---

### 2. Creare modulo `src\config\terminology.py`

1. In **VS Code**, dentro `src/config`, crea il file:

   - `terminology.py`

2. Inserisci il seguente codice:

```python
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict

import yaml


TERMINOLOGY_PATH = Path("conf") / "ops" / "terminology.yml"


@lru_cache(maxsize=1)
def load_terminology() -> Dict[str, Dict[str, str]]:
    if not TERMINOLOGY_PATH.exists():
        return {"default": {}}

    with TERMINOLOGY_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Ci aspettiamo una struttura: tenant -> {term_key -> label}
    term_map: Dict[str, Dict[str, str]] = {}
    for tenant, mapping in data.items():
        if isinstance(mapping, dict):
            term_map[str(tenant)] = {str(k): str(v) for k, v in mapping.items()}
    return term_map


def get_label(term_key: str, tenant: str | None = None) -> str:
    term_map = load_terminology()
    tenant_key = tenant or "default"

    if tenant_key in term_map and term_key in term_map[tenant_key]:
        return term_map[tenant_key][term_key]

    # Fallback: se non esiste per tenant specifico, prova default
    default_map = term_map.get("default", {})
    if term_key in default_map:
        return default_map[term_key]

    # Fallback finale: ritorna la chiave stessa
    return term_key
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/config/terminology.py` con `load_terminology` e `get_label`


---

### 3. Uso della terminologia nella UI (es. Streamlit)

> Qui dipende da come hai scritto la UI, ma ti do un esempio generico per Streamlit.

1. Apri il file della dashboard principale, es. `src/ui/dashboard.py`.
2. In cima, aggiungi:

```python
from src.config.terminology import get_label
```

3. Supponiamo che tu abbia del testo come:

```python
st.subheader("Analisi attacchi e breakdown convogli")
```

modificalo così:

```python
label_attack = get_label("attack")
label_breakdown = get_label("breakdown")
label_convoy = get_label("convoy")

st.subheader(f"Analisi {label_attack} e {label_breakdown} {label_convoy}")
```

4. Più avanti, ogni volta che hai una label “sensibile”/specifica, usa `get_label`.

5. Salva il file.

> In futuro potrai passare il parametro `tenant` (es. letto da ambiente o da un file di config)
> per cambiare le terminologie a seconda dell’installazione.

**Checklist (fine Giorno 2)**
- [ ] Esiste un file `terminology.yml` con mapping default
- [ ] La UI inizia a usare `get_label(...)` per alcune label


---

## Giorno 3 – Audit log decisioni operatore vs modello/RL

### Obiettivo del giorno
- Registrare da qualche parte le decisioni umane vs suggerimenti del modello/RL,
- iniziare a tenere uno **storico di governance** per auditing futuro.


---

### 1. Creare cartella e file di audit log

1. In **Esplora File** o VS Code, crea la cartella:

   - `logs/audit`

   Da terminale:

```bash
mkdir logs\audit
```

2. Il logger per le API esiste già (`logs/api/api.log`); qui userai un file separato,
   ad esempio `logs/audit/decisions.log`.

**Checklist**
- [ ] Esiste `logs/audit`


---

### 2. Creare `src\api\audit_logging.py`

1. In **VS Code**, nella cartella `src/api`, crea il file:

   - `audit_logging.py`

2. Inserisci:

```python
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


AUDIT_LOG_DIR = Path("logs") / "audit"
AUDIT_LOG_FILE = AUDIT_LOG_DIR / "decisions.log"


@dataclass
class DecisionRecord:
    timestamp_utc: str
    user_id: str | None
    convoy_id: str | None
    scenario_id: str | None
    source: str  # es. "rl_suggestion", "human_override"
    action_taken: str  # es. "go_to_W3", "hold_2", "reroute"
    action_suggested: str | None
    model_version: str | None
    notes: str | None = None
    extra: Dict[str, Any] | None = None


def get_audit_logger() -> logging.Logger:
    AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("audit")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        fh = logging.FileHandler(AUDIT_LOG_FILE, encoding="utf-8")
        fmt = logging.Formatter("%(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


def log_decision(record: DecisionRecord) -> None:
    logger = get_audit_logger()
    payload = asdict(record)
    logger.info(json.dumps(payload, ensure_ascii=False))
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/api/audit_logging.py` con `DecisionRecord` e `log_decision`


---

### 3. Integrare l’audit logging in un flusso decisionale

> Dipende da come hai modellato la parte di RL / HITL.  
> Ti propongo un punto di integrazione **semplice**: quando l’operatore conferma o modifica
> una decisione suggerita.

Supponiamo che tu abbia un endpoint tipo `/optimize` o simile dove:

- il sistema propone un’azione (`action_suggested`),
- l’utente ne sceglie una (`action_taken`).

1. Apri l’endpoint più vicino a questo flusso, es. in `src/api/app.py` (o file correlato).
2. Aggiungi gli import:

```python
from src.api.audit_logging import DecisionRecord, log_decision
from src.ml.model_info import get_model_version
```

3. Quando hai `action_taken` e (se c’è) `action_suggested`, crea un record:

```python
timestamp_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
model_version = None
try:
    model_version = get_model_version("models/risk_model.pkl")
except Exception:
    model_version = None

record = DecisionRecord(
    timestamp_utc=timestamp_utc,
    user_id=None,  # puoi mettere un ID pseudonimo se lo hai
    convoy_id=convoy_id,  # se disponibile nel contesto
    scenario_id=None,
    source="human_override" if action_taken != action_suggested else "rl_suggestion",
    action_taken=str(action_taken),
    action_suggested=str(action_suggested) if action_suggested is not None else None,
    model_version=model_version,
    notes=None,
    extra={},
)

log_decision(record)
```

4. Salva il file.

> Anche se non hai ancora tutta la UI HITL perfetta, vale la pena avere già pronto
> questo meccanismo di logging per quando estenderai le funzioni.


**Checklist**
- [ ] Esiste un file `logs/audit/decisions.log` che si popola quando un’azione viene confermata
- [ ] Il record contiene almeno timestamp, action_taken, action_suggested, model_version


---

### 4. (Facoltativo) Nota nel README su audit log

1. Apri `README.md`.
2. Aggiungi una breve menzione alla sezione log/ops, ad esempio:

```markdown
Gli override e le decisioni confermate dall'operatore vengono registrati in:

- `logs/audit/decisions.log`

Ogni riga è un JSON con timestamp, azione suggerita/effettiva, eventuale convoy_id e
versione del modello corrente, per facilitare audit e analisi future.
```

3. Salva il file.

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] Sanitizzazione base PII attiva
- [ ] Terminologia neutra configurata e usata in almeno un punto della UI
- [ ] Audit log decisioni operative attivo e funzionante


---

Con la Parte 1 della Fase 23 hai portato nel codice alcuni elementi chiave di **etica e governance**:

- log meno “curiosi” e più rispettosi della privacy,
- terminologia configurabile per adattarsi a contesti diversi,
- prime tracce di audit log per decisioni umane vs modello/RL.

Nella **Parte 2** ti concentrerai su **circuit breaker**, retention di log/report
e **licensing** (Apache-2.0 + note per componenti proprietari).
