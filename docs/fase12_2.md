# Fase 12 – Governance Modello & Licensing (Parte 2, Giorni 4–6, Windows)

> **Scopo Parte 2**  
> Chiudere la Fase 12 dando al progetto:
>
> - una base di **governance del modello** (versioni, audit delle chiamate),
> - una struttura di **licensing chiara** (ossatura dual license: core vs plugin),
> - documentazione aggiornata nel README e in `docs/etica_terminologia_licensing.md`.

> **Prerequisiti:**
> - Parte 1 completata (`fase12_1.md`),
> - training modello rischio funzionante (`python -m src.ml.train_risk_model`),
> - API `/predict` funzionante.


---

## Struttura Parte 2

- **Giorno 4** – Aggiungere `model_version` al report di training e all’API
- **Giorno 5** – Log basico delle chiamate `/predict` (audit)
- **Giorno 6** – Licensing: `LICENSE`, struttura `plugins/` e aggiornamento docs


---

## Giorno 4 – `model_version` in training & API

### Obiettivo del giorno
- Introdurre un campo `model_version` nel report JSON di training,
- includerlo nella risposta dell’API `/predict`,
- preparare il terreno per audit futuri.


---

### 1. Aggiungere `model_version` in `train_risk_model.py`

1. Apri `src\ml\train_risk_model.py`.
2. Nella funzione `train_risk_model`, prima di costruire `report_dict`, genera una semplice `model_version`.

Ad esempio, subito prima di `report_dict = { ... }`, aggiungi:

```python
    from datetime import datetime

    # Versione modello: timestamp ISO semplice (puoi sostituirlo con qualcosa di più evoluto in futuro)
    model_version = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
```

3. Quando costruisci `report_dict`, aggiungi il campo `model_version`:

```python
    report_dict = {
        "model_version": model_version,
        "params": {
            "test_size": test_size,
            "random_state": random_state,
            "max_iter": max_iter,
        },
        "metrics": {
            "classification_report": classification_report(
                y_test, y_pred, digits=3, output_dict=True
            ),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        },
    }
```

4. Salva il file.

**Checklist**
- [ ] `train_risk_model` calcola una stringa `model_version`
- [ ] `model_version` è salvata dentro `risk_model.report.json`


---

### 2. Aggiungere una piccola utility per leggere `model_version`

1. In `src\ml`, crea il file `model_info.py` (se non esiste).
2. Inserisci il seguente contenuto:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import json


def load_model_report(model_path: str | Path) -> Dict[str, Any]:
    """Carica il report JSON associato al modello.

    Esempio:
    - model_path: "models/risk_model.pkl" → report: "models/risk_model.report.json"
    """
    path = Path(model_path)
    report_path = path.with_suffix(".report.json")
    if not report_path.exists():
        raise FileNotFoundError(f"Report del modello non trovato: {report_path}")

    with report_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_model_version(model_path: str | Path) -> str | None:
    """Ritorna la versione del modello leggendo il report JSON.

    Se il campo non esiste, restituisce None.
    """
    try:
        report = load_model_report(model_path)
    except FileNotFoundError:
        return None

    return report.get("model_version")
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\ml\model_info.py` con `get_model_version("models/risk_model.pkl")`


---

### 3. Includere `model_version` nella risposta API `/predict`

1. Apri `src\api\app.py`.
2. Aggiungi l’import:

```python
from src.ml.model_info import get_model_version
```

3. Aggiorna il modello `PredictResponse` per includere il campo `model_version`:

```python
class PredictResponse(BaseModel):
    """Schema della risposta per /predict."""

    schema_version: str
    model_version: str | None = None
    total_minutes: int
    timestep_minutes: int
    n_convoys: int
    risk_threshold_used: float
    results: list[ConvoyRisk]
```

4. Dentro `predict_risk`, prima di costruire il `PredictResponse`, ottieni la versione modello:

```python
    model_version = get_model_version("models/risk_model.pkl")
```

5. Quando crei `PredictResponse`, aggiungi `model_version=model_version`:

```python
    response = PredictResponse(
        schema_version="1.0",
        model_version=model_version,
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        risk_threshold_used=RISK_THRESHOLD_DEFAULT,
        results=results,
    )
```

6. Salva il file.

**Checklist (fine Giorno 4)**
- [ ] `risk_model.report.json` contiene `model_version`
- [ ] L’API `/predict` restituisce un campo `model_version` nella risposta
- [ ] Non ci sono errori di import (`get_model_version` trovata)  


---

## Giorno 5 – Log basico delle chiamate `/predict`

### Obiettivo del giorno
- Aggiungere un log CSV semplice per le chiamate a `/predict`, utile per **audit**:
  - parametri di input,
  - modello usato,
  - timestamp,
  - qualche KPI della risposta.


---

### 1. Creare un modulo `api_audit.py`

1. In `src\api`, crea il file `api_audit.py`.
2. Inserisci il seguente contenuto:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from datetime import datetime

import csv

AUDIT_DIR = Path("data") / "audit"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def log_predict_call(payload: Dict[str, Any], response: Dict[str, Any]) -> None:
    """Logga una chiamata all'endpoint /predict in un CSV di audit.

    Il log e' pensato per fini di governance, non per PII:
    - timestamp UTC
    - parametri di input principali
    - versione modello
    - soglia utilizzata
    - numero di convogli richiesti e quanti ad alto rischio.
    """
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = AUDIT_DIR / "predict_calls.csv"

    timestamp_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    total_minutes = int(payload.get("total_minutes", 0))
    timestep_minutes = int(payload.get("timestep_minutes", 0))
    n_convoys = int(payload.get("n_convoys", 0))

    model_version = response.get("model_version")
    threshold_used = float(response.get("risk_threshold_used", 0.0))

    results = response.get("results", [])
    n_results = len(results)
    n_high_risk = sum(1 for r in results if bool(r.get("is_high_risk")))

    row = {
        "ts_utc": timestamp_utc,
        "total_minutes": total_minutes,
        "timestep_minutes": timestep_minutes,
        "n_convoys": n_convoys,
        "n_results": n_results,
        "n_high_risk": n_high_risk,
        "model_version": model_version or "",
        "risk_threshold_used": threshold_used,
    }

    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\api\api_audit.py` con `log_predict_call`


---

### 2. Chiamare `log_predict_call` dentro l’endpoint `/predict`

1. Apri `src\api\app.py`.
2. Aggiungi l’import in cima al file:

```python
from src.api.api_audit import log_predict_call
```

3. Dentro la funzione `predict_risk`, **dopo** aver costruito `response` (prima del `return`), aggiungi:

```python
    # Audit di base: logghiamo la chiamata (senza PII)
    try:
        log_predict_call(request.dict(), response.dict())
    except Exception as exc:  # noqa: BLE001
        # Non vogliamo che un problema di logging blocchi l'API
        print(f"[WARN] Impossibile loggare la chiamata /predict: {exc}")
```

4. Salva il file.

**Checklist**
- [ ] `predict_risk` chiama `log_predict_call(...)` prima del `return`
- [ ] Eventuali errori di logging vengono gestiti in modo “soft” (print + continua)


---

### 3. Verifica rapida dell’audit CSV

1. Avvia l’API:

```bash
uvicorn src.api.app:app --reload
```

2. Effettua 1–2 chiamate a `/predict` (da Swagger UI o dallo script che hai creato nelle fasi precedenti).
3. Controlla, con Esplora File o VS Code, la cartella:

   - `data/audit/predict_calls.csv`

4. Apri il CSV e verifica che le righe abbiano campi del tipo:

   - `ts_utc`
   - `total_minutes`
   - `timestep_minutes`
   - `n_convoys`
   - `n_results`
   - `n_high_risk`
   - `model_version`
   - `risk_threshold_used`

**Checklist (fine Giorno 5)**
- [ ] Le chiamate a `/predict` generano righe in `data/audit/predict_calls.csv`
- [ ] Il log non contiene PII (solo parametri tecnici e versioni modello)  


---

## Giorno 6 – Licensing: LICENSE, struttura plugin & docs

### Obiettivo del giorno
- Dare una struttura chiara al licensing:
  - aggiungere un file `LICENSE` per il core (es. Apache-2.0),
  - creare una cartella `plugins/` per codice potenzialmente proprietario,
  - aggiornare README e `docs/etica_terminologia_licensing.md`.


---

### 1. Aggiungere il file `LICENSE` (core open source)

1. Nella root del progetto, crea un file chiamato `LICENSE`.
2. Scarica o copia dal sito ufficiale il testo della **Apache License 2.0**  
   (cerca su internet “Apache License 2.0 testo ufficiale”) e incollalo nel file `LICENSE`.

> Non c’è bisogno di modificarlo, se non per eventuali note standard (nome autore, anno).  
> Per un progetto personale puoi anche lasciarlo “generico” e indicare il tuo nome nell’intestazione.

**Checklist**
- [ ] Esiste un file `LICENSE` con il testo della Apache-2.0 (o altra licenza da te scelta)


---

### 2. Creare cartella `plugins/` e README

1. Nella root del progetto, crea una cartella `plugins`.
2. Dentro `plugins`, crea un file `README.md`.
3. Inserisci, ad esempio:

```markdown
# Plugins & Connettori

Questa cartella e' pensata per contenere codice opzionale (plugin, connettori,
integrazioni con sistemi esterni).

Per impostazione predefinita, il core del progetto (cartella `src/` e file principali)
e' rilasciato sotto licenza **Apache-2.0** (vedi file `LICENSE`).

I file e sotto-cartelle dentro `plugins/` possono avere **licenze diverse**,
ad esempio proprietarie o soggette a contratti separati. In tal caso:

- specificare chiaramente la licenza nel `README.md` della singola sotto-cartella,
- evitare di includere qui codice che non hai il diritto di ridistribuire.
```

4. Salva il file.

**Checklist**
- [ ] Esiste la cartella `plugins/` con un README che spiega la logica “dual” core vs plugin


---

### 3. Aggiornare README con sezione “Licenza”

1. Apri `README.md`.
2. Aggiungi (o modifica) una sezione “Licenza”, ad esempio:

```markdown
## Licenza

Il core del progetto (cartella `src/` e file principali alla radice del repository)
e' rilasciato sotto licenza **Apache-2.0**. Vedi il file:

- `LICENSE`

La cartella `plugins/` e' pensata per contenere estensioni, connettori o integrazioni
che possono essere soggette a licenze diverse (incluse licenze proprietarie).
In tal caso, ogni plugin dovrebbe avere un proprio `README.md` con note di licensing.
```

3. Salva il README.

**Checklist**
- [ ] Il README spiega chiaramente la licenza del core e il ruolo di `plugins/`


---

### 4. Aggiornare `docs/etica_terminologia_licensing.md`

1. Apri `docs/etica_terminologia_licensing.md`.
2. Aggiorna/integra la sezione **5. Licensing**, ad esempio:

```markdown
## 5. Licensing

- Il core del progetto (simulatore, modello di rischio, API, UI di base) e' pensato per
  una licenza open source (es. Apache-2.0).
- Il file `LICENSE` alla radice del repository definisce la licenza del core.
- La cartella `plugins/` e' prevista per componenti opzionali che possono avere
  licenze diverse (es. plugin proprietari, connettori specifici per sistemi esterni).
```

3. Salva il file.

**Checklist (fine Giorno 6 – fine Parte 2)**
- [ ] Esiste `LICENSE` con la licenza scelta per il core
- [ ] Esiste `plugins/` con README che spiega l’approccio
- [ ] README e `docs/etica_terminologia_licensing.md` sono aggiornati con la parte Licensing


---

## Fine Fase 12 – Cosa hai ottenuto

Con la Fase 12 completata hai dato al progetto:

- una **base etica & privacy** esplicita (no PII, data minimization, docs dedicate),
- un primo **controllo automatico** per evitare colonne PII nei dataset/log,
- una struttura di **terminologia configurabile** per scenari multi-tenant,
- elementi di **governance del modello** (model_version, report di training, audit CSV),
- una struttura di **licensing chiara**: core open source + spazio per plugin con licenze diverse.

Questi elementi ti permettono di:

- ragionare in modo più maturo su privacy e governance,
- documentare le scelte fatte,
- preparare il terreno per futuri passi “enterprise” (es. retention policy, DPIA formale, CI con controlli di sicurezza, ecc.).
