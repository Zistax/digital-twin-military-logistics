# Fase 10 – API rafforzata (simulate + contract predict) – Parte 1 (Giorni 1–3, Windows)

> **Scopo Fase 10 (visione generale)**  
> Far assomigliare la tua API a qualcosa di **più vicino a un prodotto reale**, aggiungendo:
>
> - un endpoint `POST /simulate` che lancia la simulazione e restituisce un riassunto,
> - un endpoint `POST /predict` (alias di `/predict_risk`) con un **contratto un po’ più strutturato**,
> - una documentazione Swagger più chiara grazie a tag e modelli di richiesta/risposta.

In **Parte 1** sistemi solo il lato **API FastAPI**.  
In **Parte 2** collegherai meglio la **UI Streamlit** all’API.

> **Prerequisiti**:
> - Fase 06 (API) completata: esiste `src\api\app.py` con `/health` e `/predict_risk`,
> - Fase 08 (soglia rischio) completata: `PredictResponse` restituisce `risk_threshold_used`,
> - Fase 09 (config) completata: puoi lanciare simulazioni e training normalmente.


---

## Struttura Fase 10 – Parte 1

- **Giorno 1** – Aggiungere alias `POST /predict` e arricchire il contratto di richiesta/risposta
- **Giorno 2** – Aggiungere `POST /simulate` che chiama il simulatore e calcola KPI base
- **Giorno 3** – Testare gli endpoint da Swagger UI e da script Python


---

## Giorno 1 – Alias `/predict` e piccolo contratto versione

### Obiettivo del giorno
- Esporre l’endpoint di rischio non solo come `/predict_risk` ma anche come `/predict`,
- aggiungere un campo `schema_version` nella richiesta e nella risposta,
- organizzare meglio la doc Swagger con un tag `["risk"]`.


---

### 1. Aprire `src\api\app.py` e aggiungere un campo `schema_version`

1. Apri **VS Code**.
2. Apri il file `src\api\app.py`.
3. Cerca la definizione della classe `PredictRequest` (Pydantic).  
   Dovrebbe essere simile a quella creata in Fase 06 / 08.

Aggiornala in questo modo (aggiungendo il campo `schema_version` con default `"1.0"`):

```python
class PredictRequest(BaseModel):
    """Schema della richiesta per /predict (rischio convoglio)."""

    schema_version: str = Field(
        "1.0",
        description="Versione dello schema di richiesta. Permette di evolvere l'API in futuro.",
    )
    total_minutes: int = Field(120, gt=0, description="Durata totale simulazione (minuti)")
    timestep_minutes: int = Field(10, gt=0, description="Durata di ogni passo (minuti)")
    n_convoys: int = Field(5, gt=0, description="Numero di convogli da valutare")
```

Salva il file.

**Checklist**
- [ ] `PredictRequest` contiene ora il campo `schema_version` con default `"1.0"`


---

### 2. Aggiungere `schema_version` anche nella risposta

Cerca la definizione di `PredictResponse`. Dovrebbe già contenere (almeno):

- `total_minutes`
- `timestep_minutes`
- `n_convoys`
- `risk_threshold_used`
- `results: list[ConvoyRisk]`

Aggiorna la classe aggiungendo `schema_version`:

```python
class PredictResponse(BaseModel):
    """Schema della risposta per /predict."""

    schema_version: str
    total_minutes: int
    timestep_minutes: int
    n_convoys: int
    risk_threshold_used: float
    results: list[ConvoyRisk]
```

Salva il file.

**Checklist**
- [ ] `PredictResponse` contiene il campo `schema_version`


---

### 3. Restituire `schema_version` dalla funzione `predict_risk`

Nella funzione `predict_risk`, quando crei l’oggetto `PredictResponse`, aggiungi `schema_version="1.0"`.

Trova il punto in cui hai qualcosa del genere:

```python
    response = PredictResponse(
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        risk_threshold_used=RISK_THRESHOLD_DEFAULT,
        results=results,
    )
```

Sostituiscilo con:

```python
    response = PredictResponse(
        schema_version="1.0",
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        risk_threshold_used=RISK_THRESHOLD_DEFAULT,
        results=results,
    )
```

Salva il file.

**Checklist**
- [ ] `predict_risk` include `schema_version="1.0"` nella risposta


---

### 4. Esporre sia `/predict_risk` sia `/predict` con lo stesso handler

Ora vogliamo che lo **stesso** handler serva sia il vecchio percorso `/predict_risk` sia quello nuovo `/predict`.

Sopra la definizione di `predict_risk`, modifica i decorator FastAPI.

Se prima avevi:

```python
@app.post("/predict_risk", response_model=PredictResponse)
def predict_risk(request: PredictRequest) -> PredictResponse:
    ...
```

sostituisci con:

```python
@app.post("/predict_risk", response_model=PredictResponse, tags=["risk"])
@app.post("/predict", response_model=PredictResponse, tags=["risk"])
def predict_risk(request: PredictRequest) -> PredictResponse:
    ...
```

> In questo modo:
> - il percorso “storico” `/predict_risk` continua a funzionare,
> - il nuovo percorso “pulito” `/predict` è disponibile,
> - entrambi sono raggruppati sotto il tag `risk` nella Swagger UI.

Salva il file.

**Checklist**
- [ ] `predict_risk` ha due decorator: `/predict_risk` e `/predict`
- [ ] Entrambi hanno `tags=["risk"]`


---

### 5. Verifica rapida che l’app si importi ancora

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python -c "from src.api.app import app; print('OK', app.title)"
```

Dovresti vedere qualcosa tipo:

```text
OK Digital Twin Logistico – API Rischio Convoglio
```

**Checklist (fine Giorno 1)**
- [ ] `app` è importabile senza errori
- [ ] `PredictRequest` e `PredictResponse` contengono `schema_version`
- [ ] `predict_risk` ha doppio decorator (`/predict_risk` e `/predict`) con tag `risk`


---

## Giorno 2 – Aggiungere `POST /simulate` (simulazione + KPI base)

### Obiettivo del giorno
- Esporre un endpoint `POST /simulate` che:
  - riceve i parametri di simulazione,
  - costruisce un `SimConfig`,
  - chiama `run_simulation(config, save_to_csv=True)`,
  - calcola alcuni KPI base,
  - restituisce un riassunto JSON.

Userai:

- `SimConfig` e `run_simulation` da `src.sim.core`,
- `compute_basic_kpis` e/o `load_events_csv` da `src.sim.metrics`.


---

### 1. Aggiungere gli import necessari

In cima a `src\api\app.py`, insieme agli altri import, aggiungi:

```python
from src.sim.core import SimConfig, run_simulation
from src.sim.metrics import compute_basic_kpis, load_events_csv
```

> Se i nomi dei moduli sono leggermente diversi (es. `from src.sim import core`), adatta gli import al tuo codice effettivo; nella Fase 02 e 03 hai creato proprio questi file.

Salva il file.

**Checklist**
- [ ] `app.py` importa `SimConfig`, `run_simulation`, `compute_basic_kpis`, `load_events_csv`


---

### 2. Definire i modelli Pydantic per `/simulate`

Sotto le classi collegate al rischio (`PredictRequest`, `ConvoyRisk`, `PredictResponse`), aggiungi le classi Pydantic per la simulazione:

```python
class SimulateRequest(BaseModel):
    """Parametri per eseguire una simulazione singola."""

    schema_version: str = Field(
        "1.0",
        description="Versione dello schema di richiesta per /simulate.",
    )
    total_minutes: int = Field(120, gt=0, description="Durata totale simulazione (minuti)")
    timestep_minutes: int = Field(10, gt=0, description="Durata di ogni passo (minuti)")
    n_convoys: int = Field(5, gt=0, description="Numero di convogli simulati")
    depot_capacity: int = Field(2, gt=0, description="Capacità del deposito")
    simulation_name: str = Field("api_run", description="Nome logico della simulazione")


class SimulationKPI(BaseModel):
    """KPI riassuntivi della simulazione."""

    n_convoys: int
    n_completed_convoys: int
    n_not_completed_convoys: int
    avg_completion_minute: float | None = None
    min_completion_minute: float | None = None
    max_completion_minute: float | None = None


class SimulateResponse(BaseModel):
    """Risposta di /simulate."""

    schema_version: str
    simulation_name: str
    total_minutes: int
    timestep_minutes: int
    n_convoys: int
    depot_capacity: int
    final_minute: int
    events_csv_path: str | None = None
    kpi: SimulationKPI
```

Salva il file.

**Checklist**
- [ ] `SimulateRequest`, `SimulationKPI` e `SimulateResponse` sono definiti in `app.py`


---

### 3. Implementare l’endpoint `POST /simulate`

Sotto la funzione `predict_risk`, aggiungi l’endpoint FastAPI:

```python
@app.post("/simulate", response_model=SimulateResponse, tags=["simulation"])
def simulate(request: SimulateRequest) -> SimulateResponse:
    """Esegue una simulazione singola e restituisce un riassunto.

    Usa run_simulation(...) per generare gli eventi e calcola alcuni KPI base.
    """
    # Costruiamo un SimConfig a partire dalla richiesta
    config = SimConfig(
        simulation_name=request.simulation_name,
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        depot_capacity=request.depot_capacity,
    )

    # Eseguiamo la simulazione; salviamo gli eventi in CSV
    events, summary = run_simulation(config, save_to_csv=True)

    # Prendiamo eventuale percorso del CSV dagli summary
    events_csv_path: str | None = summary.get("events_csv_path")

    # Calcoliamo KPI base usando il modulo metrics
    if events_csv_path:
        df_events = load_events_csv(events_csv_path)
    else:
        # Se per qualche motivo il path non c'è, costruiamo un DataFrame dagli eventi in memoria
        import pandas as pd

        df_events = pd.DataFrame(events)

    kpi_dict = compute_basic_kpis(df_events)

    kpi = SimulationKPI(
        n_convoys=int(kpi_dict.get("n_convoys", summary.get("n_convoys", 0))),
        n_completed_convoys=int(
            kpi_dict.get("n_completed_convoys", summary.get("n_completed_convoys", 0))
        ),
        n_not_completed_convoys=int(
            kpi_dict.get("n_not_completed_convoys", summary.get("n_not_completed_convoys", 0))
        ),
        avg_completion_minute=kpi_dict.get("avg_completion_minute"),
        min_completion_minute=kpi_dict.get("min_completion_minute"),
        max_completion_minute=kpi_dict.get("max_completion_minute"),
    )

    response = SimulateResponse(
        schema_version="1.0",
        simulation_name=summary.get("simulation_name", request.simulation_name),
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        depot_capacity=request.depot_capacity,
        final_minute=int(summary.get("final_minute", request.total_minutes)),
        events_csv_path=events_csv_path,
        kpi=kpi,
    )

    return response
```

> Se il tuo `SimConfig` ha parametri leggermente diversi, adatta il costruttore.  
> In Fase 02 abbiamo usato proprio questi nomi, quindi dovresti essere allineato.

Salva il file.

**Checklist**
- [ ] Esiste la funzione `simulate` con decorator `@app.post("/simulate", ...)`
- [ ] All’interno di `simulate` viene costruito un `SimConfig` e chiamato `run_simulation`
- [ ] `SimulateResponse` viene popolato con `summary` e con KPI derivati da `compute_basic_kpis`


---

### 4. Verifica che l’app si importi ancora

Nel terminale, dalla root del progetto (con `.venv` attivo):

```bash
python -c "from src.api.app import app; print('OK endpoints', [r.path for r in app.routes])"
```

Dovresti vedere un elenco di percorsi che include almeno:

- `/health`
- `/predict_risk`
- `/predict`
- `/simulate`

**Checklist (fine Giorno 2)**
- [ ] L’import rapido di `app` funziona
- [ ] Nell’elenco dei percorsi vedi `/simulate`


---

## Giorno 3 – Test manuale di `/predict` e `/simulate` da Swagger UI e script

### Obiettivo del giorno
- Avviare il server API con Uvicorn,
- testare manualmente `/predict` e `/simulate` da Swagger UI,
- fare un piccolo test da Python con `requests` (facoltativo, ma utile in vista della Fase 10 Parte 2).


---

### 1. Avviare il server API con Uvicorn

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
uvicorn src.api.app:app --reload
```

Attendi che compaia il messaggio simile a:

```text
Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Lascia questo terminale aperto.


---

### 2. Testare `/predict` dalla Swagger UI

1. Apri il browser e vai su:

```text
http://127.0.0.1:8000/docs
```

2. Dovresti vedere gli endpoint sotto i tag **risk** e **simulation**.
3. Clicca su **POST /predict** → **Try it out**.
4. Nel body di esempio troverai anche `schema_version`:

```json
{
  "schema_version": "1.0",
  "total_minutes": 120,
  "timestep_minutes": 10,
  "n_convoys": 5
}
```

5. Clicca su **Execute**.

Dovresti vedere una risposta tipo:

```json
{
  "schema_version": "1.0",
  "total_minutes": 120,
  "timestep_minutes": 10,
  "n_convoys": 5,
  "risk_threshold_used": 0.50,
  "results": [
    {
      "convoy_id": 1,
      "risk_proba": 0.123,
      "is_high_risk": false
    },
    ...
  ]
}
```

**Checklist**
- [ ] `POST /predict` risponde con `schema_version` e `risk_threshold_used`
- [ ] I risultati contengono `convoy_id`, `risk_proba`, `is_high_risk`


---

### 3. Testare `/simulate` dalla Swagger UI

Sempre in `http://127.0.0.1:8000/docs`:

1. Clicca su **POST /simulate** (tag `simulation`) → **Try it out**.
2. Il corpo di default sarà simile a:

```json
{
  "schema_version": "1.0",
  "total_minutes": 120,
  "timestep_minutes": 10,
  "n_convoys": 5,
  "depot_capacity": 2,
  "simulation_name": "api_run"
}
```

3. Clicca su **Execute**.

Se tutto funziona, vedrai una risposta con struttura simile:

```json
{
  "schema_version": "1.0",
  "simulation_name": "api_run",
  "total_minutes": 120,
  "timestep_minutes": 10,
  "n_convoys": 5,
  "depot_capacity": 2,
  "final_minute": 120,
  "events_csv_path": "data/raw/sim_events_20251116_153000.csv",
  "kpi": {
    "n_convoys": 5,
    "n_completed_convoys": 4,
    "n_not_completed_convoys": 1,
    "avg_completion_minute": 87.5,
    "min_completion_minute": 60.0,
    "max_completion_minute": 120.0
  }
}
```

> I numeri saranno diversi, ma la **struttura** deve essere quella.

**Checklist**
- [ ] `POST /simulate` risponde con i campi base e i KPI
- [ ] Il campo `events_csv_path` punta a un CSV dentro `data\raw`


---

### 4. (Facoltativo) Test da script Python con `requests`

Se non lo hai ancora fatto in passato, questo è un buon momento per aggiungere `requests` in `requirements.txt` e installarlo:

Nel file `requirements.txt` aggiungi (se non c’è):

```txt
requests
```

Poi, nel terminale con `.venv` attivo:

```bash
pip install -r requirements.txt
```

Ora puoi creare un piccolo script di prova (ad esempio `notebooks/test_api_predict.py` o `scripts/test_api_predict.py`).

Esempio di contenuto:

```python
import requests

base_url = "http://127.0.0.1:8000"

payload = {
    "schema_version": "1.0",
    "total_minutes": 120,
    "timestep_minutes": 10,
    "n_convoys": 3,
}

resp = requests.post(f"{base_url}/predict", json=payload)
print("Status:", resp.status_code)
print("JSON:", resp.json())
```

E uno analogo per `/simulate`.

**Checklist (fine Giorno 3)**
- [ ] Posso chiamare `/predict` e `/simulate` da Swagger UI senza errori
- [ ] (Facoltativo) Ho testato `/predict` e/o `/simulate` da uno script Python con `requests`
- [ ] Capisco cosa restituisce ogni endpoint


---

Con questa Parte 1 della Fase 10, l’API è più completa e il contratto del rischio convoglio è più esplicito.  
Nella **Parte 2** collegherai la UI Streamlit all’API (invece di chiamare direttamente le funzioni Python).