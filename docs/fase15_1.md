# Fase 15 – /optimize & motore scenari (Parte 1, Giorni 1–3, Windows)

> **Obiettivo pratico**  
> Costruire un primo endpoint **`POST /optimize`** che usa l’env RL di scenario
> (`ConvoyScenarioEnv`) per confrontare le azioni (politiche logistiche) già definite:
>
> - aggiungere un piccolo **motore di valutazione** delle azioni,
> - esporlo via API FastAPI come `/optimize`,
> - avere anche un **test automatico** per l’endpoint.
>
> Nessun algoritmo RL vero e proprio: per ora facciamo solo “simula tutte le azioni
> N volte e confrontale”.


---

## Struttura Fase 15 – Parte 1

- **Giorno 1** – Motore scenari RL (`src/rl/optimizer.py`)
- **Giorno 2** – Modelli Pydantic e endpoint `POST /optimize`
- **Giorno 3** – Test automatico per `/optimize` e prova manuale da Swagger


---

## Giorno 1 – Motore scenari RL (`src/rl/optimizer.py`)

### Obiettivo del giorno
- Creare un modulo che:
  - usa `ConvoyScenarioEnv`,
  - per ogni azione lancia più episodi,
  - calcola statistiche semplici (media reward, media KPI),
  - restituisce un elenco di risultati per azione.


---

### 1. Creare `src\rl\optimizer.py`

1. In **VS Code**, nella cartella `src\rl`, crea un nuovo file:

   - `optimizer.py`

2. Incolla questo codice:

```python
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Sequence

from src.rl.env import ConvoyScenarioEnv, EpisodeResult


@dataclass
class ActionStats:
    """Statistiche aggregate per una singola azione RL."""

    action_id: int
    action_name: str
    n_episodes: int
    avg_reward: float
    reward_std: Optional[float]
    mean_n_not_completed_convoys: Optional[float]
    mean_avg_completion_minute: Optional[float]


def _extract_kpi_value(kpi_list: Sequence[Dict[str, Any]], key: str) -> Optional[float]:
    """Estrae in modo robusto un valore numerico medio da una lista di KPI."""
    vals = []
    for k in kpi_list:
        if key in k and k[key] is not None:
            try:
                vals.append(float(k[key]))
            except (TypeError, ValueError):
                continue

    if not vals:
        return None

    return float(mean(vals))


def evaluate_actions(
    num_episodes_per_action: int = 3,
    actions_filter: Optional[Sequence[int]] = None,
) -> List[ActionStats]:
    """Valuta ciascuna azione RL con piu' episodi di simulazione.

    - num_episodes_per_action: quante simulazioni eseguire per ogni azione.
    - actions_filter: se non None, limita la valutazione solo a questi action_id.

    Ritorna una lista di ActionStats con reward medio e KPI medi.
    """
    if num_episodes_per_action <= 0:
        raise ValueError("num_episodes_per_action deve essere >= 1")

    env = ConvoyScenarioEnv()
    all_actions = env.actions

    if actions_filter is not None:
        actions_filter_set = {int(a) for a in actions_filter}
        actions = [a for a in all_actions if int(a["id"]) in actions_filter_set]
    else:
        actions = all_actions

    if not actions:
        raise RuntimeError("Nessuna azione da valutare (controlla conf/rl/default.yml)")

    results: List[ActionStats] = []

    for action in actions:
        rewards: List[float] = []
        kpis: List[Dict[str, Any]] = []

        action_id = int(action["id"])
        action_name = str(action.get("name", f"action_{action_id}"))

        for _ in range(num_episodes_per_action):
            ep_res: EpisodeResult = env.run_episode(action_id=action_id)
            rewards.append(float(ep_res.reward))
            kpis.append(ep_res.kpi)

        avg_reward = float(mean(rewards))
        reward_std = float(pstdev(rewards)) if len(rewards) > 1 else None

        mean_n_not_completed = _extract_kpi_value(
            kpis, "n_not_completed_convoys"
        )
        mean_avg_completion = _extract_kpi_value(
            kpis, "avg_completion_minute"
        )

        results.append(
            ActionStats(
                action_id=action_id,
                action_name=action_name,
                n_episodes=num_episodes_per_action,
                avg_reward=avg_reward,
                reward_std=reward_std,
                mean_n_not_completed_convoys=mean_n_not_completed,
                mean_avg_completion_minute=mean_avg_completion,
            )
        )

    # Ordiniamo per reward decrescente (migliore per primo)
    results.sort(key=lambda x: x.avg_reward, reverse=True)
    return results
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\rl\optimizer.py`
- [ ] La funzione `evaluate_actions` restituisce una lista di `ActionStats`


---

### 2. Prova veloce da REPL (facoltativo ma consigliato)

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python
```

2. Nel REPL Python:

```python
from src.rl.optimizer import evaluate_actions

stats = evaluate_actions(num_episodes_per_action=2)

for s in stats:
    print(
        f"action={s.action_id} ({s.action_name}), "
        f"episodes={s.n_episodes}, avg_reward={s.avg_reward:.2f}, "
        f"mean_not_completed={s.mean_n_not_completed_convoys}, "
        f"mean_avg_completion={s.mean_avg_completion_minute}"
    )
```

3. Controlla che vengano stampate alcune righe, una per azione.

4. Esci dal REPL:

```python
exit()
```

**Checklist (fine Giorno 1)**
- [ ] `evaluate_actions(...)` gira senza errori
- [ ] Vedi qualche statistica per le azioni definite in `conf/rl/default.yml`


---

## Giorno 2 – Modelli Pydantic & endpoint `POST /optimize`

### Obiettivo del giorno
- Aggiungere i modelli Pydantic per richiesta/risposta,
- creare l’endpoint `/optimize` in `src/api/app.py`,
- collegarlo al motore `evaluate_actions`.


---

### 1. Definire i modelli Pydantic in `src\api\app.py`

1. Apri `src\api\app.py`.
2. Vicino agli altri modelli (es. `PredictRequest`, `PredictResponse`), aggiungi:

```python
class OptimizeRequest(BaseModel):
    """Richiesta per /optimize: confronta politiche logistiche di alto livello."""

    schema_version: str = "1.0"
    n_episodes_per_action: int = Field(
        3, ge=1, le=20, description="Numero di simulazioni per ciascuna azione"
    )
    actions: list[int] | None = Field(
        default=None,
        description="Lista opzionale di action_id da valutare; se None, usa tutte le azioni.",
    )


class OptimizeActionResult(BaseModel):
    action_id: int
    action_name: str
    n_episodes: int
    avg_reward: float
    reward_std: float | None = None
    mean_n_not_completed_convoys: float | None = None
    mean_avg_completion_minute: float | None = None


class OptimizeResponse(BaseModel):
    schema_version: str
    model_version: str | None = None
    results: list[OptimizeActionResult]
```

> Per `Field` assicurati di avere l’import in cima al file:
>
> ```python
> from pydantic import BaseModel, Field
> ```

3. Salva il file.

**Checklist**
- [ ] In `app.py` esistono `OptimizeRequest`, `OptimizeActionResult`, `OptimizeResponse`
- [ ] `Field` è importato da `pydantic`


---

### 2. Aggiungere l’endpoint `/optimize` in FastAPI

1. Sempre in `src\api\app.py`, aggiungi l’import del motore RL e della funzione `get_model_version` se non c’è già:

```python
from src.rl.optimizer import evaluate_actions
from src.ml.model_info import get_model_version
```

2. Sotto gli altri endpoint (`/predict`, `/simulate`), aggiungi il nuovo handler:

```python
@app.post("/optimize", response_model=OptimizeResponse, tags=["rl"])
def optimize(request: OptimizeRequest) -> OptimizeResponse:
    """Confronta le azioni RL di alto livello eseguendo simulazioni per ciascuna.

    Per ogni azione definita in conf/rl (o sottoinsieme richiesto), lancia
    `n_episodes_per_action` episodi di simulazione usando `ConvoyScenarioEnv`,
    e restituisce reward medio + KPI medi.
    """
    # Determiniamo quali azioni valutare (se l'utente ha passato un filtro)
    actions_filter = request.actions if request.actions else None

    # Eseguiamo la valutazione
    stats = evaluate_actions(
        num_episodes_per_action=request.n_episodes_per_action,
        actions_filter=actions_filter,
    )

    # Model version (per governance); se non esiste ancora il report, sara' None
    model_version = get_model_version("models/risk_model.pkl")

    results = [
        OptimizeActionResult(
            action_id=s.action_id,
            action_name=s.action_name,
            n_episodes=s.n_episodes,
            avg_reward=s.avg_reward,
            reward_std=s.reward_std,
            mean_n_not_completed_convoys=s.mean_n_not_completed_convoys,
            mean_avg_completion_minute=s.mean_avg_completion_minute,
        )
        for s in stats
    ]

    return OptimizeResponse(
        schema_version=request.schema_version,
        model_version=model_version,
        results=results,
    )
```

3. Salva il file.

**Checklist**
- [ ] Esiste un handler `@app.post("/optimize", ...)` in `app.py`
- [ ] L’endpoint chiama `evaluate_actions(...)` e restituisce `OptimizeResponse`


---

### 3. Avviare l’API e controllare Swagger

1. Nel terminale (con `.venv` attivo), dalla root del progetto, avvia l’API:

```bash
uvicorn src.api.app:app --reload
```

2. Apri il browser su:

- `http://127.0.0.1:8000/docs`

3. Dovresti vedere anche l’endpoint:

- `POST /optimize` (tag: `rl`)

4. Cliccaci sopra, apri i dettagli del modello di richiesta/risposta.

**Checklist (fine Giorno 2)**
- [ ] L’API parte senza errori di import
- [ ] In Swagger UI compare `POST /optimize` con il modello giusto


---

## Giorno 3 – Test automatico & prova manuale di `/optimize`

### Obiettivo del giorno
- Aggiungere un test semplice per verificare che `/optimize` risponda,
- fare 1–2 prove manuali da Swagger UI o da script `requests`.


---

### 1. Aggiungere il test `tests\test_api_optimize.py`

1. In **VS Code**, nella cartella `tests`, crea il file:

   - `test_api_optimize.py`

2. Inserisci questo contenuto (adatta se hai già una `TestClient` pronta):

```python
from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


def test_optimize_endpoint_basic():
    payload = {
        "schema_version": "1.0",
        "n_episodes_per_action": 1
    }

    resp = client.post("/optimize", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "schema_version" in data
    assert "results" in data

    results = data["results"]
    assert isinstance(results, list)
    assert len(results) >= 1

    first = results[0]
    assert "action_id" in first
    assert "avg_reward" in first
```

3. Salva il file.

**Checklist**
- [ ] Esiste `tests\test_api_optimize.py` con un test base sull’endpoint


---

### 2. Eseguire il test con pytest

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest tests/test_api_optimize.py
```

Oppure, se preferisci far girare l’intera suite:

```bash
pytest
```

Se tutto è a posto, il test deve passare.

> Se il test è lento (la simulazione richiede un po’ di tempo), puoi:
> - usare una config di simulazione “più corta” per i test (es. `conf/sim/dev.yml`),
> - oppure impostare `n_episodes_per_action=1` come nel test di esempio.


**Checklist**
- [ ] Il test `test_api_optimize.py` gira e passa
- [ ] Nessun nuovo errore introdotto nella suite di test


---

### 3. Prova manuale da Swagger UI

1. Avvia di nuovo l’API (se non è già in esecuzione):

```bash
uvicorn src.api.app:app --reload
```

2. Apri `http://127.0.0.1:8000/docs` nel browser.
3. Seleziona `POST /optimize` → **Try it out**.
4. Inserisci un payload semplice, ad esempio:

```json
{
  "schema_version": "1.0",
  "n_episodes_per_action": 1
}
```

5. Clicca su **Execute**.
6. Controlla nella risposta JSON:
   - lista di risultati (`results`),
   - `action_id`, `action_name`, `avg_reward`, KPI medi.

> Non serve interpretare ancora il valore assoluto del reward,
> l’importante è che l’endpoint funzioni e che dia risultati coerenti.

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] `/optimize` è visibile e utilizzabile da Swagger UI
- [ ] Esiste un test per `/optimize` che passa
- [ ] Il motore `evaluate_actions` è collegato correttamente all’API
