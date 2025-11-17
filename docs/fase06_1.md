# Fase 06 – API REST per il rischio convoglio (Parte 1, Giorni 1–3, Windows)

> **Scopo Fase 06 (visione generale)**  
> Esporre il modello di rischio tramite una **API REST** locale, in modo che tu possa:
>
> - chiamare un endpoint HTTP `/predict_risk`,
> - passare i parametri di scenario (durata, timestep, numero convogli),
> - ottenere una risposta JSON con la probabilità di rischio per ogni convoglio.
>
> In **Parte 1** ti occupi di:
> - installare FastAPI + Uvicorn,
> - creare la struttura `src\api`,
> - creare un'app FastAPI con `/health`,
> - aggiungere l'endpoint `/predict_risk` che usa il modello salvato.

> **Prerequisiti**: Fase 05 completata, in particolare:
> - esiste `models\risk_model.pkl`,
> - funzionano `python -m src.ml.train_risk_model` e `python -m src.ml.predict_cli`,
> - `pytest` gira senza errori.

---

## Struttura Fase 06 – Parte 1

- **Giorno 1** – Aggiungere FastAPI + Uvicorn e creare struttura `src\api`
- **Giorno 2** – Creare l'app FastAPI con `/health` e `/predict_risk`
- **Giorno 3** – Avviare il server API e testarlo dal browser e da script Python

---

## Giorno 1 – Installare FastAPI + Uvicorn e creare `src\api`

### Obiettivo del giorno
- Aggiungere **FastAPI** e **Uvicorn** alle dipendenze,
- creare la cartella `src\api`,
- creare il file `src\api\__init__.py` (vuoto).

---

### 1. Aggiornare `requirements.txt`

1. Apri `requirements.txt` nella root del progetto.
2. Aggiungi queste righe (se non ci sono già):

```txt
fastapi
uvicorn
```

3. Salva il file.

**Checklist**
- [ ] `requirements.txt` contiene anche `fastapi` e `uvicorn`

---

### 2. Installare i nuovi pacchetti

1. Apri **PowerShell** o **cmd**.
2. Vai nella cartella del progetto (sostituisci `TUO_UTENTE`):

```bash
cd C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico
```

3. Attiva l'ambiente virtuale `.venv`:

- PowerShell:
  ```bash
  .venv\Scripts\Activate.ps1
  ```
- cmd:
  ```bat
  .venv\Scripts\activate.bat
  ```

4. Installa/aggiorna i pacchetti:

```bash
pip install -r requirements.txt
```

Attendi la fine dell'installazione.

**Checklist**
- [ ] Ambiente `.venv` attivo
- [ ] `pip install -r requirements.txt` eseguito senza errori bloccanti

---

### 3. Creare la struttura `src\api`

1. In **VS Code**, nella barra laterale:
   - clic destro su `src` → **New Folder** → digita `api`
2. Dentro `src\api`, crea un file vuoto `__init__.py`.

In alternativa, da terminale (facoltativo):

```bash
mkdir src\api
type NUL > src\api\__init__.py
```

**Checklist (fine Giorno 1)**
- [ ] Esiste la cartella `src\api`
- [ ] Esiste il file `src\api\__init__.py` (può essere vuoto)
- [ ] FastAPI e Uvicorn risultano installati (`pip show fastapi`, `pip show uvicorn` opzionale)

---

## Giorno 2 – Creare l'app FastAPI con `/health` e `/predict_risk`

### Obiettivo del giorno
- Creare `src\api\app.py` con una **FastAPI app**,
- aggiungere un endpoint `/health` per verificare che il server risponda,
- aggiungere un endpoint `/predict_risk` che:
  - riceve JSON con parametri di scenario,
  - carica il modello `risk_model.pkl`,
  - usa `predict_convoy_risk_proba` per calcolare le probabilità,
  - restituisce JSON con i risultati.

---

### 1. Creare `src\api\app.py` con l'app FastAPI base

1. In VS Code, sotto `src\api`, crea il file `app.py`.
2. Inserisci questo contenuto iniziale:

```python
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="Digital Twin Logistico – API Rischio Convoglio",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict:
    """Endpoint di health-check semplice."""
    return {"status": "ok"}
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\api\app.py`
- [ ] L'app FastAPI è definita con `app = FastAPI(...)`
- [ ] Esiste una funzione `health_check` decorata con `@app.get("/health")`

---

### 2. Aggiungere l'endpoint `/predict_risk`

Nello stesso file `src\api\app.py`, **sotto** la definizione di `health_check`, aggiungi il resto del codice:

```python
from pydantic import BaseModel, Field

from src.ml.predict import load_risk_model, predict_convoy_risk_proba


class PredictRequest(BaseModel):
    """Schema della richiesta per /predict_risk."""

    total_minutes: int = Field(120, gt=0, description="Durata totale simulazione (minuti)")
    timestep_minutes: int = Field(10, gt=0, description="Durata di ogni passo (minuti)")
    n_convoys: int = Field(5, gt=0, description="Numero di convogli da valutare")


class ConvoyRisk(BaseModel):
    """Rappresenta il rischio stimato per un singolo convoglio."""

    convoy_id: int
    risk_proba: float


class PredictResponse(BaseModel):
    """Schema della risposta per /predict_risk."""

    total_minutes: int
    timestep_minutes: int
    n_convoys: int
    results: list[ConvoyRisk]


@app.post("/predict_risk", response_model=PredictResponse)
def predict_risk(request: PredictRequest) -> PredictResponse:
    """Calcola la probabilità di rischio per ogni convoglio."""
    # Carichiamo il modello (in una versione più avanzata potremmo farlo solo una volta)
    model = load_risk_model("models/risk_model.pkl")

    df_result = predict_convoy_risk_proba(
        model,
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
    )

    results = [
        ConvoyRisk(convoy_id=int(row["convoy_id"]), risk_proba=float(row["risk_proba"]))
        for _, row in df_result.iterrows()
    ]

    response = PredictResponse(
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        results=results,
    )

    return response
```

Verifica che **tutto il file** `app.py` contenga sia la definizione di `app` che gli import e le classi aggiuntive.

> **Attenzione**: assicurati che la riga  
> `from src.ml.predict import load_risk_model, predict_convoy_risk_proba`  
> sia presente e che il percorso corrisponda a quanto creato in Fase 05.

**Checklist**
- [ ] `PredictRequest`, `ConvoyRisk`, `PredictResponse` sono definiti in `app.py`
- [ ] Esiste la funzione `predict_risk` con decoratore `@app.post("/predict_risk", response_model=PredictResponse)`
- [ ] Dentro `predict_risk` viene chiamato `load_risk_model("models/risk_model.pkl")`
- [ ] Dentro `predict_risk` viene chiamato `predict_convoy_risk_proba(...)`

---

### 3. Controllo veloce di sintassi

Nel terminale (con `.venv` attivo), esegui un controllo minimo importando l'app:

```bash
python -c "from src.api.app import app; print('OK', app.title)"
```

Dovresti vedere qualcosa come:

```text
OK Digital Twin Logistico – API Rischio Convoglio
```

Se ottieni errori di import (percorso, nome modulo, ecc.), rientra in VS Code e correggi.

**Checklist (fine Giorno 2)**
- [ ] Posso importare `app` da `src.api.app` senza errori
- [ ] Il comando di controllo stampa "OK ..." come atteso

---

## Giorno 3 – Avviare il server API e testare gli endpoint

### Obiettivo del giorno
- Avviare il server FastAPI con Uvicorn,
- verificare l'endpoint `/health` dal browser,
- verificare l'endpoint `/predict_risk` dall'interfaccia interattiva **Swagger UI** di FastAPI,
- fare un piccolo test da script Python.

---

### 1. Avviare il server API (Uvicorn)

Nel terminale (con `.venv` attivo), dalla cartella del progetto:

```bash
uvicorn src.api.app:app --reload
```

- Se tutto va bene, vedrai dei log tipo:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
...
```

> **Nota**: lascia questo terminale aperto finché vuoi mantenere il server attivo.

**Checklist**
- [ ] `uvicorn src.api.app:app --reload` parte senza errori
- [ ] Vedo nei log che il server è in ascolto su `http://127.0.0.1:8000`

---

### 2. Testare `/health` dal browser

1. Apri il browser (Chrome, Edge, ecc.).
2. Vai all'indirizzo:

```text
http://127.0.0.1:8000/health
```

Dovresti vedere una risposta JSON minimale, ad esempio:

```json
{"status": "ok"}
```

**Checklist**
- [ ] `/health` risponde con `{"status": "ok"}`

---

### 3. Usare la Swagger UI per testare `/predict_risk`

FastAPI espone automaticamente una UI interattiva.

1. Nel browser, vai a:

```text
http://127.0.0.1:8000/docs
```

2. Dovresti vedere la documentazione con:
   - `GET /health`
   - `POST /predict_risk`

3. Clicca su **POST /predict_risk**, poi su **Try it out**.

4. Nel corpo JSON di esempio, vedrai qualcosa tipo:

```json
{
  "total_minutes": 120,
  "timestep_minutes": 10,
  "n_convoys": 5
}
```

Puoi:
- lasciare i valori di default,
- oppure modificarli (es. `n_convoys`: 3).

5. Clicca su **Execute**.

Se il modello `models\risk_model.pkl` esiste e il resto è corretto, dovresti vedere una risposta simile a:

```json
{
  "total_minutes": 120,
  "timestep_minutes": 10,
  "n_convoys": 5,
  "results": [
    {
      "convoy_id": 1,
      "risk_proba": 0.123
    },
    ...
  ]
}
```

Se vedi un errore tipo "File modello non trovato", significa che devi eseguire prima:

```bash
python -m src.ml.train_risk_model
```

**Checklist**
- [ ] Posso aprire `http://127.0.0.1:8000/docs` e vedere la Swagger UI
- [ ] Posso chiamare `POST /predict_risk` dalla Swagger UI e ottenere una risposta valida

---

### 4. Test rapido da script Python (facoltativo ma utile)

Per abituarti all'uso dell'API da codice, puoi creare un piccolo script in `notebooks` o in una cartella a parte (es. `scripts` se la crei).

Esempio veloce (da eseguire in un notebook o file `.py`):

```python
import requests

url = "http://127.0.0.1:8000/predict_risk"

payload = {
    "total_minutes": 120,
    "timestep_minutes": 10,
    "n_convoys": 3,
}

response = requests.post(url, json=payload)
print("Status code:", response.status_code)
print("JSON:", response.json())
```

> Per usare questo esempio hai bisogno di `requests` installato. Se vuoi, puoi aggiungere `requests` a `requirements.txt` e installarlo.

**Checklist (fine Giorno 3)**

- [ ] So avviare il server API con `uvicorn src.api.app:app --reload`
- [ ] Posso verificare `/health` dal browser
- [ ] Posso usare la Swagger UI per chiamare `/predict_risk`
- [ ] (Facoltativo) Ho testato la chiamata API anche da script Python

---

Quando questi passi sono completati, puoi passare alla **Parte 2 della Fase 06** (`fase06_2.md`), dove aggiungerai **test automatici per l'API**, eventualmente aggiornerai `run_checks.bat` e farai il **commit Git di chiusura Fase 06**.
