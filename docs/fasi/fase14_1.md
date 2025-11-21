# Fase 14 – RL scaffolding (env di scenario) – Parte 1, Giorni 1–3, Windows

> **Scopo Fase 14 (visione generale)**  
> Iniziare a preparare il terreno per una futura **policy RL** senza entrare ancora
> in algoritmi complessi:
>
> - definire alcune **azioni di scenario** (politiche logistiche) configurabili,
> - creare una piccola **config RL** (`conf/rl/default.yml`),
> - costruire un **env di scenario** che lancia il simulatore e calcola un reward.
>
> In questa parte userai il simulatore come una “scatola nera”:
> un episodio = 1 simulazione con parametri diversi.

> **Niente deep learning** per ora: solo struttura, config e un env Python pulito.

> **Prerequisiti:**
> - Fino alla Fase 13 completata,
> - il simulatore funziona (`python -m src.sim.main_sim`),
> - l’API `/simulate` funziona (Fase 10),
> - i moduli `SimConfig`, `run_simulation`, `compute_basic_kpis` esistono.


---

## Struttura Fase 14 – Parte 1

- **Giorno 1** – Definire config RL (`conf/rl/default.yml`) con le azioni di scenario
- **Giorno 2** – Creare il loader RL (`src/config/rl_loader.py`)
- **Giorno 3** – Creare l’env di scenario (`src/rl/env.py`) e provarlo da REPL


---

## Giorno 1 – Config RL: `conf/rl/default.yml`

### Obiettivo del giorno
- Aggiungere una config RL separata, che definisce:
  - un elenco di **azioni** (scenari),
  - pesi del **reward** calcolato dai KPI del simulatore.


---

### 1. Creare cartella `conf/rl`

1. In **VS Code**, nella sidebar, espandi la cartella `conf`.
2. Se non esiste ancora, crea una nuova cartella `rl`:

   - clic destro su `conf` → **New Folder** → `rl`

Oppure da terminale (facoltativo):

```bash
mkdir conf\rl
```

**Checklist**
- [ ] Esiste la cartella `conf\rl`


---

### 2. Creare `conf\rl\default.yml`

1. In VS Code, clic destro su `conf\rl` → **New File** → `default.yml`.
2. Inserisci questo contenuto base (puoi adattare i numeri in futuro):

```yaml
rl:
  # Elenco di azioni/scenari che l'agente potra' scegliere.
  # Per ora pensiamo a 3 politiche logistiche diverse.
  actions:
    - id: 0
      name: "conservative"
      description: "Meno convogli, deposito piu' capiente (piu' sicuro, meno throughput)."
      overrides:
        n_convoys: 3
        depot_capacity: 3

    - id: 1
      name: "balanced"
      description: "Configurazione bilanciata (default)."
      overrides:
        n_convoys: 5
        depot_capacity: 2

    - id: 2
      name: "aggressive"
      description: "Molti convogli, deposito meno capiente (piu' throughput, piu' rischio)."
      overrides:
        n_convoys: 7
        depot_capacity: 1

  # Pesi per il calcolo del reward a partire dai KPI della simulazione.
  reward:
    w_not_completed: 2.0     # penalizza convogli non completati
    w_avg_completion: 1.0    # penalizza tempi medi di completamento alti
    w_high_risk: 1.0         # (per futuri KPI legati al rischio, opzionale)

  # Numero di episodi da eseguire per un run "di prova" (usato piu' avanti)
  episodes_per_run: 10
```

3. Salva il file.

> Per ora stai solo descrivendo **3 scenari** diversi di utilizzo del simulatore.
> L’agent RL in futuro potrà imparare a scegliere tra questi.

**Checklist**
- [ ] Esiste `conf\rl\default.yml` con sezioni `rl.actions` e `rl.reward`


---

### 3. Collegare questa config alla documentazione

Apri `README.md` e, se vuoi, aggiungi una nota nella sezione sul simulatore / config, ad esempio:

```markdown
Sono definiti alcuni scenari di politica logistica (per un futuro uso RL) in:

- `conf/rl/default.yml`

Ogni azione rappresenta una configurazione diversa di parametri di simulazione
(es. numero di convogli, capacita' del deposito).
```

Salva il `README.md`.

**Checklist (fine Giorno 1)**
- [ ] `conf/rl/default.yml` creato e leggibile
- [ ] Il README accenna (anche brevemente) agli scenari RL


---

## Giorno 2 – Loader RL: `src/config/rl_loader.py`

### Obiettivo del giorno
- Creare un piccolo modulo che carica la config RL (`conf/rl/*.yml`),
- metterlo vicino agli altri loader (`config_loader.py`, `terminology_loader.py`).


---

### 1. Creare `src\config\rl_loader.py`

1. In VS Code, apri la cartella `src\config`.
2. Crea un nuovo file: `rl_loader.py`.
3. Inserisci questo codice:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, TypedDict

import os
import yaml


BASE_CONF_DIR = Path("conf")


class RLAction(TypedDict):
    id: int
    name: str
    description: str
    overrides: Dict[str, Any]


class RLRewardWeights(TypedDict, total=False):
    w_not_completed: float
    w_avg_completion: float
    w_high_risk: float


def load_rl_config(env: str | None = None) -> Dict[str, Any]:
    """Carica la configurazione RL da conf/rl/{env}.yml.

    - env: nome ambiente (default, dev...). Se None, legge RL_ENV o 'default'.
    """
    if env is None:
        env = os.environ.get("RL_ENV", "default")

    path = BASE_CONF_DIR / "rl" / f"{env}.yml"
    if not path.exists():
        raise FileNotFoundError(f"File di configurazione RL non trovato: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"La configurazione RL in {path} non contiene un dict valido.")

    rl_conf = data.get("rl", data)
    return rl_conf


def get_rl_actions(env: str | None = None) -> List[RLAction]:
    """Ritorna la lista di azioni RL definite in conf/rl/{env}.yml."""
    rl_conf = load_rl_config(env)
    actions_raw = rl_conf.get("actions", [])
    actions: List[RLAction] = []

    for item in actions_raw:
        # Normalizziamo i campi minimi, con default sensati.
        action: RLAction = RLAction(
            id=int(item.get("id", len(actions))),
            name=str(item.get("name", f"action_{len(actions)}")),
            description=str(item.get("description", "")),
            overrides=dict(item.get("overrides", {})),
        )
        actions.append(action)

    return actions


def get_reward_weights(env: str | None = None) -> RLRewardWeights:
    """Ritorna i pesi del reward definiti nella sezione rl.reward."""
    rl_conf = load_rl_config(env)
    reward_raw = rl_conf.get("reward", {})

    weights: RLRewardWeights = RLRewardWeights(
        w_not_completed=float(reward_raw.get("w_not_completed", 2.0)),
        w_avg_completion=float(reward_raw.get("w_avg_completion", 1.0)),
        w_high_risk=float(reward_raw.get("w_high_risk", 1.0)),
    )
    return weights
```

4. Salva il file.

**Checklist**
- [ ] Esiste `src\config\rl_loader.py` con `load_rl_config`, `get_rl_actions`, `get_reward_weights`


---

### 2. Testare il loader RL da REPL

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python
```

2. Nel REPL Python:

```python
from src.config.rl_loader import load_rl_config, get_rl_actions, get_reward_weights

rl_conf = load_rl_config()
print("RL conf keys:", rl_conf.keys())

actions = get_rl_actions()
print("Azioni RL:")
for a in actions:
    print(" -", a["id"], a["name"], a["overrides"])

weights = get_reward_weights()
print("Reward weights:", weights)
```

Dovresti vedere qualcosa del tipo:

```text
RL conf keys: dict_keys(['actions', 'reward', 'episodes_per_run'])
Azioni RL:
  - 0 conservative {'n_convoys': 3, 'depot_capacity': 3}
  - 1 balanced {'n_convoys': 5, 'depot_capacity': 2}
  - 2 aggressive {'n_convoys': 7, 'depot_capacity': 1}
Reward weights: {'w_not_completed': 2.0, 'w_avg_completion': 1.0, 'w_high_risk': 1.0}
```

3. Esci dal REPL:

```python
exit()
```

**Checklist (fine Giorno 2)**
- [ ] `load_rl_config()` legge correttamente `conf/rl/default.yml`
- [ ] `get_rl_actions()` restituisce le 3 azioni attese
- [ ] `get_reward_weights()` restituisce i pesi del reward


---

## Giorno 3 – Env di scenario: `src/rl/env.py`

### Obiettivo del giorno
- Creare una classe `ConvoyScenarioEnv` che:
  - legge la config simulazione + config RL,
  - costruisce un `SimConfig` diverso a seconda dell’azione,
  - lancia una simulazione,
  - calcola alcuni KPI con `compute_basic_kpis`,
  - restituisce un **reward** + dettagli episodio.


---

### 1. Creare il package `src\rl`

1. In VS Code, nella cartella `src`, crea una nuova cartella `rl`.
2. Dentro `src\rl`, crea un file vuoto `__init__.py`.

Oppure da terminale:

```bash
mkdir src\rl
type NUL > src\rl\__init__.py
```

**Checklist**
- [ ] Esiste `src\rl`
- [ ] Esiste `src\rl\__init__.py`


---

### 2. Creare `src\rl\env.py`

1. In `src\rl`, crea il file `env.py`.
2. Inserisci questo codice (adatta i nomi se nel tuo progetto sono leggermente diversi):

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.config.config_loader import load_sim_config
from src.config.rl_loader import get_rl_actions, get_reward_weights, RLAction
from src.sim.core import SimConfig, run_simulation
from src.sim.metrics import compute_basic_kpis, load_events_csv


@dataclass
class EpisodeResult:
    action_id: int
    action_name: str
    reward: float
    kpi: Dict[str, Any]
    summary: Dict[str, Any]
    events_csv_path: str | None


class ConvoyScenarioEnv:
    """Env di alto livello: un episodio = 1 simulazione con uno scenario.

    Non e' un env OpenAI Gym completo, ma una struttura semplice per sperimentare:
    - scegli un'azione (scenario logistico),
    - lanciamo il simulatore,
    - calcoliamo KPI,
    - calcoliamo un reward scalare.
    """

    def __init__(self, sim_env: str | None = None, rl_env: str | None = None) -> None:
        # Config simulazione (valori di base)
        self._sim_conf_dict = load_sim_config(sim_env)
        # Azioni RL e pesi reward
        self._actions: List[RLAction] = get_rl_actions(rl_env)
        self._reward_weights = get_reward_weights(rl_env)

    @property
    def actions(self) -> List[RLAction]:
        return self._actions

    def _build_sim_config_for_action(self, action: RLAction) -> SimConfig:
        """Costruisce un SimConfig applicando gli overrides dell'azione."""
        # Partiamo dai default della simulazione
        base = dict(self._sim_conf_dict)

        # Applichiamo gli overrides definiti nell'azione
        overrides = action.get("overrides", {})
        base.update(overrides)

        # Creiamo il SimConfig; adatta i parametri se la tua classe ha nomi diversi
        config = SimConfig(
            simulation_name=f"rl_action_{action['id']}_{action['name']}",
            total_minutes=int(base.get("total_minutes", 120)),
            timestep_minutes=int(base.get("timestep_minutes", 10)),
            n_convoys=int(base.get("n_convoys", 5)),
            depot_capacity=int(base.get("depot_capacity", 2)),
        )
        return config

    def _compute_reward(self, kpi: Dict[str, Any]) -> float:
        """Calcola un reward scalare a partire dai KPI e dai pesi."""
        w = self._reward_weights

        n_not_completed = int(kpi.get("n_not_completed_convoys", 0))
        avg_completion = kpi.get("avg_completion_minute", None)

        # Penalizziamo convogli non completati e tempi medi alti
        reward = 0.0
        reward -= w.get("w_not_completed", 2.0) * n_not_completed

        if avg_completion is not None:
            reward -= w.get("w_avg_completion", 1.0) * float(avg_completion)

        # w_high_risk e' pensato per futuri KPI di rischio (per ora lasciamo 0)
        # Se in futuro aggiungi un KPI di rischio, potrai usarlo qui.

        return reward

    def run_episode(self, action_id: int) -> EpisodeResult:
        """Esegue un episodio scegliendo uno scenario tramite action_id."""
        action = self._get_action_by_id(action_id)
        config = self._build_sim_config_for_action(action)

        # Eseguiamo la simulazione; chiediamo di salvare gli eventi in CSV
        events, summary = run_simulation(config, save_to_csv=True)

        events_csv_path = summary.get("events_csv_path")
        if events_csv_path is not None:
            df_events = load_events_csv(events_csv_path)
        else:
            # Fallback: costruiamo un DataFrame direttamente dagli eventi in memoria
            import pandas as pd

            df_events = pd.DataFrame(events)

        kpi = compute_basic_kpis(df_events)
        reward = self._compute_reward(kpi)

        return EpisodeResult(
            action_id=action["id"],
            action_name=action["name"],
            reward=reward,
            kpi=kpi,
            summary=summary,
            events_csv_path=events_csv_path,
        )

    def _get_action_by_id(self, action_id: int) -> RLAction:
        for a in self._actions:
            if int(a["id"]) == int(action_id):
                return a
        raise ValueError(f"Azione RL con id={action_id} non trovata.")
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\rl\env.py` con `ConvoyScenarioEnv` e `EpisodeResult`
- [ ] L’env usa `load_sim_config`, `get_rl_actions`, `run_simulation`, `compute_basic_kpis`


---

### 3. Prova veloce da REPL (un episodio)


1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python
```

2. Nel REPL Python, prova:

```python
from src.rl.env import ConvoyScenarioEnv

env = ConvoyScenarioEnv()

for a in env.actions:
    print("Azione:", a["id"], a["name"], a["overrides"])

# Eseguiamo un episodio con l'azione 1 (balanced)
result = env.run_episode(action_id=1)

print("Reward:", result.reward)
print("KPI:", result.kpi)
print("Summary:", result.summary)
print("CSV eventi:", result.events_csv_path)
```

> La prima volta la simulazione potrebbe metterci qualche secondo,
> ma l’importante è che non ci siano errori di import o type error.

3. Esci dal REPL:

```python
exit()
```

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] `ConvoyScenarioEnv` viene importato senza errori
- [ ] `env.actions` restituisce la lista di scenari definiti in `conf/rl/default.yml`
- [ ] `env.run_episode(action_id=1)` esegue una simulazione e restituisce KPI + reward


---

Con questa Parte 1 hai:

- una **config RL** dedicata (`conf/rl/default.yml`),
- un **loader RL** riutilizzabile (`rl_loader.py`),
- un **env di scenario** `ConvoyScenarioEnv` che ti permette di:
  - scegliere uno scenario,
  - lanciare il simulatore,
  - calcolare un reward.

Nella **Parte 2** (`fase14_2.md`) userai questo env per costruire:
- un piccolo **random baseline** (policy che sceglie azioni a caso),
- logging degli episodi (`data/rl/episodes_random.csv`),
- test minimi e nota nel README.
