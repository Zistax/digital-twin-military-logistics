# Fase 14 – RL scaffolding (random baseline & logging) – Parte 2, Giorni 4–6, Windows

> **Scopo Parte 2**  
> Usare l’env di scenario creato in Parte 1 per:
>
> - implementare una **random policy** (sceglie azioni a caso),
> - loggare gli episodi in un CSV dedicato,
> - aggiungere test minimi,
> - documentare nel README come usare questo “playground RL”.

> **Prerequisiti:**
> - Parte 1 completata (`fase14_1.md`),
> - `ConvoyScenarioEnv` funziona,
> - il simulatore gira senza errori.


---

## Struttura Parte 2

- **Giorno 4** – Script `random_baseline` per eseguire più episodi
- **Giorno 5** – Test minimi su env RL
- **Giorno 6** – Aggiornare README, prova completa e commit Git


---

## Giorno 4 – Script `random_baseline`

### Obiettivo del giorno
- Creare uno script `src/rl/random_baseline.py` che:
  - istanzia `ConvoyScenarioEnv`,
  - esegue N episodi scegliendo azioni casuali,
  - salva un CSV `data/rl/episodes_random.csv` con reward e KPI.


---

### 1. Creare cartella `data/rl`

1. In **File Explorer** o VS Code, nella cartella `data`, crea la cartella `rl`:

   - `data/rl`

Oppure da terminale:

```bash
mkdir data\rl
```

**Checklist**
- [ ] Esiste `data\rl`


---

### 2. Creare `src\rl\random_baseline.py`

1. In VS Code, dentro `src\rl`, crea il file `random_baseline.py`.
2. Inserisci il seguente codice:

```python
from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import List

from src.rl.env import ConvoyScenarioEnv, EpisodeResult
from src.config.rl_loader import load_rl_config


EPISODES_CSV_DIR = Path("data") / "rl"
EPISODES_CSV_PATH = EPISODES_CSV_DIR / "episodes_random.csv"


def run_random_baseline(num_episodes: int | None = None) -> List[EpisodeResult]:
    """Esegue una policy random su ConvoyScenarioEnv e logga gli episodi.

    - num_episodes: se None, legge rl.episodes_per_run da conf/rl/default.yml
    """
    rl_conf = load_rl_config()
    default_episodes = int(rl_conf.get("episodes_per_run", 10))

    if num_episodes is None:
        num_episodes = default_episodes

    env = ConvoyScenarioEnv()
    actions = env.actions

    if not actions:
        raise RuntimeError("Nessuna azione RL definita in conf/rl/default.yml")

    EPISODES_CSV_DIR.mkdir(parents=True, exist_ok=True)

    results: List[EpisodeResult] = []

    with EPISODES_CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "episode",
            "action_id",
            "action_name",
            "reward",
            "n_convoys",
            "n_completed_convoys",
            "n_not_completed_convoys",
            "avg_completion_minute",
            "min_completion_minute",
            "max_completion_minute",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for ep in range(num_episodes):
            action = random.choice(actions)
            action_id = int(action["id"])
            result = env.run_episode(action_id=action_id)
            results.append(result)

            kpi = result.kpi

            writer.writerow(
                {
                    "episode": ep,
                    "action_id": result.action_id,
                    "action_name": result.action_name,
                    "reward": result.reward,
                    "n_convoys": int(kpi.get("n_convoys", 0)),
                    "n_completed_convoys": int(kpi.get("n_completed_convoys", 0)),
                    "n_not_completed_convoys": int(kpi.get("n_not_completed_convoys", 0)),
                    "avg_completion_minute": kpi.get("avg_completion_minute"),
                    "min_completion_minute": kpi.get("min_completion_minute"),
                    "max_completion_minute": kpi.get("max_completion_minute"),
                }
            )

            print(
                f"[EP {ep}] action={result.action_id} ({result.action_name}) "
                f"reward={result.reward:.2f} "
                f"kpi={kpi}"
            )

    print(f"Episodi random salvati in: {EPISODES_CSV_PATH}")
    return results


def main() -> None:
    # Esegue un run standard con il numero di episodi definito in conf/rl/default.yml
    run_random_baseline()


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\rl\random_baseline.py` con `run_random_baseline` e `main()`


---

### 3. Prova lo script dalla linea di comando

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python -m src.rl.random_baseline
```

- Dovresti vedere, per ogni episodio, una riga `[EP ...]` con action, reward, KPI.
- Alla fine, un messaggio tipo:

```text
Episodi random salvati in: data/rl/episodes_random.csv
```

Apri `data/rl/episodes_random.csv` con VS Code e controlla che:

- ci siano N righe (numero di episodi),
- reward e KPI siano valorizzati.

**Checklist (fine Giorno 4)**
- [ ] `python -m src.rl.random_baseline` gira senza errori
- [ ] Il file `data/rl/episodes_random.csv` viene creato e contiene i risultati


---

## Giorno 5 – Test minimi su env RL

### Obiettivo del giorno
- Aggiungere test automatici per:
  - import di `ConvoyScenarioEnv`,
  - esecuzione di almeno un episodio con un’azione valida.


---

### 1. Creare `tests\test_rl_env.py`

1. In VS Code, nella cartella `tests`, crea il file `test_rl_env.py`.
2. Inserisci il seguente contenuto:

```python
from src.rl.env import ConvoyScenarioEnv


def test_convoy_scenario_env_basic():
    env = ConvoyScenarioEnv()
    actions = env.actions

    # Ci aspettiamo almeno un'azione definita in conf/rl/default.yml
    assert len(actions) >= 1

    # Prendiamo la prima azione e facciamo girare un episodio
    first_action_id = int(actions[0]["id"])
    result = env.run_episode(action_id=first_action_id)

    assert result.action_id == first_action_id
    assert isinstance(result.reward, (int, float))
    assert isinstance(result.kpi, dict)
```

3. Salva il file.

> Questo test è volutamente semplice: verifica solo che l’env giri almeno una volta.  
> Se in futuro la simulazione diventasse molto pesante, potresti creare una config
> `conf/sim/dev.yml` con pochi minuti di simulazione e usarla solo nei test.


**Checklist**
- [ ] Esiste `tests\test_rl_env.py` con un test base su `ConvoyScenarioEnv`


---

### 2. Lanciare `pytest` o `run_quality.bat`

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest tests/test_rl_env.py
```

oppure:

```bash
run_quality.bat
```

Assicurati che il test passi senza errori.

**Checklist (fine Giorno 5)**
- [ ] Il test `test_rl_env.py` passa
- [ ] Non ci sono nuovi errori introdotti nel resto della suite di test


---

## Giorno 6 – README, prova completa e commit

### Obiettivo del giorno
- Documentare il “playground RL” nel README,
- eseguire un giro completo (script + test),
- creare un commit Git per chiudere la Fase 14.


---

### 1. Aggiornare il README con sezione “RL scaffolding”

Apri `README.md` e aggiungi una sezione simile:

```markdown
## RL scaffolding (env di scenario)

Il progetto include una prima struttura per esperimenti RL di alto livello:

- file di config RL: `conf/rl/default.yml`
- env di scenario: `src/rl/env.py` (`ConvoyScenarioEnv`)
- script di baseline random: `src/rl/random_baseline.py`

Un episodio RL corrisponde a una simulazione completa, con parametri diversi
in base all'azione scelta (es. numero di convogli, capacita' del deposito).

Per eseguire una baseline random:

```bash
python -m src.rl.random_baseline
```

I risultati (reward + KPI per episodio) vengono salvati in:

- `data/rl/episodes_random.csv`

Questa struttura puo' essere estesa in futuro per integrare veri algoritmi RL
(es. Stable Baselines 3) utilizzando `ConvoyScenarioEnv` come env custom.
```

Salva il `README.md`.

**Checklist**
- [ ] Il README descrive come usare `ConvoyScenarioEnv` e `random_baseline`


---

### 2. Giro completo di prova

1. Esegui lo script random baseline:

```bash
python -m src.rl.random_baseline
```

2. Esegui i test (almeno quelli RL, meglio tutta la suite):

```bash
pytest
```

o

```bash
run_quality.bat
```

Controlla che:

- lo script abbia creato `data/rl/episodes_random.csv`,
- `test_rl_env.py` passi insieme al resto dei test.

**Checklist**
- [ ] Lo script random baseline funziona e crea il CSV degli episodi
- [ ] I test RL e il resto della suite passano


---

### 3. Commit Git di fine Fase 14

Nel terminale, dalla root del progetto:

```bash
git status
```

Dovresti vedere, tra gli altri:

- `conf/rl/default.yml`
- `src/config/rl_loader.py`
- `src/rl/__init__.py`
- `src/rl/env.py`
- `src/rl/random_baseline.py`
- `tests/test_rl_env.py`
- `data/rl/` (magari ignorata da `.gitignore` se non vuoi versionare i CSV)
- `README.md` aggiornato

1. Aggiungi i file (escludendo eventuali CSV se li ignori via `.gitignore`):

```bash
git add .
```

2. Crea il commit:

```bash
git commit -m "Fase 14: RL scaffolding con env di scenario e random baseline"
```

3. Verifica lo stato:

```bash
git status
```

Dovresti vedere: `nothing to commit, working tree clean`.

**Checklist (fine Giorno 6 – fine Fase 14)**
- [ ] Env RL di scenario funzionante (`ConvoyScenarioEnv`)
- [ ] Script random baseline che logga episodi in `data/rl/episodes_random.csv`
- [ ] Test base per l’env RL
- [ ] README aggiornato
- [ ] Commit Git creato per chiudere la Fase 14


---

## Fine Fase 14 – Cosa hai ottenuto

Con la Fase 14 hai:

- definito alcune **azioni di scenario** configurabili (politiche logistiche),
- creato un **env di scenario** che collega simulatore, KPI e reward,
- implementato una **random baseline** con logging degli episodi,
- aggiunto test minimi e documentazione.

Se in futuro vorrai andare oltre, potrai:

- integrare librerie RL (es. Stable Baselines) sopra `ConvoyScenarioEnv`,
- raffinare il calcolo del reward (multi-obiettivo, normalizzazione, pareto, ecc.),
- usare i CSV degli episodi per visualizzare trade-off tra reward e KPI.
