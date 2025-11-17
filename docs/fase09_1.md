# Fase 09 – Config & riproducibilità base (Parte 1, Giorni 1–3, Windows)

> **Scopo Fase 09 (visione generale)**  
> Rendere il progetto più **ordinato e riproducibile** introducendo:
>
> - una cartella di **configurazione** (`conf/`) con file YAML,
> - un piccolo modulo Python per caricare le config (`src\config\config_loader.py`),
> - l’uso di queste config come **default** per la simulazione.
>
> In **Parte 1** ti concentri su:
>
> - creare la struttura `conf/`,
> - scrivere i file YAML per simulazione e ML,
> - creare il modulo `config_loader`,
> - collegare la **simulazione** a questi file di config (come default).


> **Prerequisiti**:
> - Fino alla Fase 08 completata (almeno a grandi linee),
> - il progetto si trova in `C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico`,
> - i comandi `python -m src.sim.main_sim` e `python -m src.ml.train_risk_model` funzionano.


---

## Struttura Fase 09 – Parte 1

- **Giorno 1** – Aggiungere PyYAML e creare la cartella `conf/` con YAML base
- **Giorno 2** – Creare il modulo `src\config\config_loader.py`
- **Giorno 3** – Usare la config YAML come default in `main_sim.py`


---

## Giorno 1 – Aggiungere PyYAML e creare `conf/`

### Obiettivo del giorno
- Aggiungere la libreria **PyYAML** alle dipendenze,
- creare la cartella `conf/`,
- creare i primi file di configurazione YAML per simulazione e ML.


---

### 1. Aggiungere PyYAML a `requirements.txt`

1. Apri **VS Code**.
2. Apri il file `requirements.txt` (nella root del progetto).
3. Aggiungi una riga (se non è già presente):

```txt
PyYAML
```

4. Salva il file (`Ctrl + S`).

**Checklist**
- [ ] `requirements.txt` contiene una riga `PyYAML`


---

### 2. Installare PyYAML nell’ambiente `.venv`

1. Apri **PowerShell** o **cmd**.
2. Vai nella cartella del progetto (sostituisci `TUO_UTENTE`):

```bash
cd C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico
```

3. Attiva l’ambiente virtuale `.venv`:

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

**Checklist**
- [ ] Ambiente `.venv` attivo
- [ ] `pip install -r requirements.txt` eseguito senza errori gravi


---

### 3. Creare struttura `conf/`

Useremo una struttura molto semplice, ispirata a quella “grande” del documento di progetto, ma ridotta al minimo:

```text
conf/
  sim/
    default.yml
  ml/
    default.yml
```

1. In **VS Code**, nella barra laterale:
   - clic destro sulla root del progetto → **New Folder** → `conf`
   - clic destro su `conf` → **New Folder** → `sim`
   - clic destro su `conf` → **New Folder** → `ml`

Oppure da terminale (facoltativo):

```bash
mkdir conf
mkdir conf\sim
mkdir conf\ml
```

**Checklist**
- [ ] Esiste la cartella `conf`
- [ ] Dentro `conf` esistono `sim` e `ml`


---

### 4. Creare `conf\sim\default.yml` (config simulazione)

1. In VS Code, clic destro su `conf\sim` → **New File** → `default.yml`.
2. Inserisci questo contenuto (puoi adattare i numeri se vuoi):

```yaml
sim:
  total_minutes: 120        # durata totale simulazione (minuti)
  timestep_minutes: 10      # durata di ogni passo (minuti)
  n_convoys: 5              # numero di convogli
  depot_capacity: 2         # capacità del deposito
  random_seed: 42           # (per futuri usi di numeri casuali)
```

3. Salva il file.

**Checklist**
- [ ] Esiste `conf\sim\default.yml`
- [ ] Il file contiene una sezione `sim:` con i campi sopra


---

### 5. Creare `conf\ml\default.yml` (config ML)

1. In VS Code, clic destro su `conf\ml` → **New File** → `default.yml`.
2. Inserisci questo contenuto base:

```yaml
ml:
  test_size: 0.3            # percentuale di dati nel test set
  random_state: 42          # seed usato per train/test split e modello
  model_type: "logreg"      # per ora solo Logistic Regression
  max_iter: 1000            # max iterazioni della Logistic Regression
```

3. Salva il file.

**Checklist**
- [ ] Esiste `conf\ml\default.yml`
- [ ] Il file contiene una sezione `ml:` con i campi base


---

### 6. Verifica visiva dei file

Apri rapidamente entrambi i file in VS Code e controlla che:

- non ci siano tab strani (usa spazi, come negli esempi),
- i due file siano salvati in UTF-8 (impostazione standard di VS Code),
- la struttura rientri correttamente sotto `sim:` e `ml:`.

**Checklist (fine Giorno 1)**
- [ ] PyYAML è installato
- [ ] Esiste la struttura `conf\sim\default.yml` e `conf\ml\default.yml`
- [ ] I file YAML sono ben formati (nessun errore evidente)


---

## Giorno 2 – Modulo `config_loader` per leggere le config

### Obiettivo del giorno
- Creare un piccolo package `src\config`,
- creare `src\config\config_loader.py`,
- scrivere funzioni semplici per caricare:
  - la config simulazione (`load_sim_config`),
  - la config ML (`load_ml_config`).


---

### 1. Creare package `src\config`

1. In **VS Code**, nella barra laterale, espandi `src`.
2. Clic destro su `src` → **New Folder** → `config`.
3. Dentro `src\config`, crea un file vuoto `__init__.py`.

Oppure da terminale:

```bash
mkdir src\config
type NUL > src\config\__init__.py
```

**Checklist**
- [ ] Esiste la cartella `src\config`
- [ ] Esiste il file `src\config\__init__.py`


---

### 2. Creare `src\config\config_loader.py`

1. In VS Code, dentro `src\config`, crea il file `config_loader.py`.
2. Inserisci questo contenuto:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import os
import yaml


# Cartella base delle configurazioni
BASE_CONF_DIR = Path("conf")


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    """Carica un file YAML e restituisce un dizionario.

    Se il file non esiste, lancia FileNotFoundError.
    """
    if not path.exists():
        raise FileNotFoundError(f"File di configurazione non trovato: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Il file di configurazione {path} non contiene un dict YAML valido.")

    return data


def load_sim_config(env: str | None = None) -> Dict[str, Any]:
    """Carica la configurazione della simulazione.

    - env: nome dell'ambiente (default, dev, prod...). Se None, usa la variabile
      d'ambiente SIM_ENV, altrimenti 'default'.

    Ritorna un dict con le chiavi sotto la sezione 'sim'.
    """
    if env is None:
        env = os.environ.get("SIM_ENV", "default")

    path = BASE_CONF_DIR / "sim" / f"{env}.yml"
    raw = _load_yaml_file(path)
    sim_conf = raw.get("sim", raw)
    return sim_conf


def load_ml_config(env: str | None = None) -> Dict[str, Any]:
    """Carica la configurazione della parte ML.

    - env: nome dell'ambiente (default, dev, prod...). Se None, usa la variabile
      d'ambiente ML_ENV, altrimenti 'default'.

    Ritorna un dict con le chiavi sotto la sezione 'ml'.
    """
    if env is None:
        env = os.environ.get("ML_ENV", "default")

    path = BASE_CONF_DIR / "ml" / f"{env}.yml"
    raw = _load_yaml_file(path)
    ml_conf = raw.get("ml", raw)
    return ml_conf
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\config\config_loader.py`
- [ ] Dentro sono definite `_load_yaml_file`, `load_sim_config`, `load_ml_config`


---

### 3. Testare il loader da REPL Python

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python
```

2. Nel prompt Python, prova:

```python
from src.config.config_loader import load_sim_config, load_ml_config

sim_conf = load_sim_config()
ml_conf = load_ml_config()

print("Sim config:", sim_conf)
print("ML config:", ml_conf)
```

Dovresti vedere qualcosa del tipo:

```text
Sim config: {'total_minutes': 120, 'timestep_minutes': 10, 'n_convoys': 5, 'depot_capacity': 2, 'random_seed': 42}
ML config: {'test_size': 0.3, 'random_state': 42, 'model_type': 'logreg', 'max_iter': 1000}
```

3. Esci dal REPL:

```python
exit()
```

**Checklist (fine Giorno 2)**
- [ ] Posso caricare la config simulazione con `load_sim_config()`
- [ ] Posso caricare la config ML con `load_ml_config()`
- [ ] I dizionari risultanti contengono i valori attesi dai file YAML


---

## Giorno 3 – Usare la config YAML come default in `main_sim.py`

### Obiettivo del giorno
- Modificare `src\sim\main_sim.py` in modo che:
  - legga i **valori di default** da `conf\sim\default.yml`,
  - li usi come default negli input della CLI,
  - ma permetta comunque all’utente di sovrascriverli da tastiera.


> **Nota importante**: non cambierai il comportamento “logico” della simulazione,
> ma solo **come vengono scelti i valori di default**.

---

### 1. Aggiungere l’import in `src\sim\main_sim.py`

Apri `src\sim\main_sim.py` in VS Code.

All’inizio del file, aggiungi l’import:

```python
from src.config.config_loader import load_sim_config
```

Assicurati di non rompere altri import già presenti (es. `from .config import SimConfig`, ecc.).

**Checklist**
- [ ] `main_sim.py` importa `load_sim_config` da `src.config.config_loader`


---

### 2. Caricare i default dalla config all’interno di `main()`

Cerca la funzione `main()` in `main_sim.py` (l’avevi creata in Fase 02).  
All’inizio di `main()`, subito dopo la stampa iniziale, aggiungi qualcosa come:

```python
def main() -> None:
    print("=== Simulatore logistico – Fase 02+ (con config YAML) ===")

    # Carichiamo i valori di default dalla config YAML
    sim_conf = load_sim_config()

    default_total_minutes = int(sim_conf.get("total_minutes", 120))
    default_timestep_minutes = int(sim_conf.get("timestep_minutes", 10))
    default_n_convoys = int(sim_conf.get("n_convoys", 5))
    default_depot_capacity = int(sim_conf.get("depot_capacity", 2))
```

Poi, più in basso, dove usi le funzioni tipo `ask_int(...)` per leggere i parametri da tastiera, sostituisci i vecchi valori di default (es. 120, 10, 5, ecc.) con questi nuovi:

```python
    total_minutes = ask_int("Durata totale simulazione (minuti)", default_total_minutes)
    timestep_minutes = ask_int("Durata di ogni passo (minuti)", default_timestep_minutes)
    n_convoys = ask_int("Numero di convogli", default_n_convoys)
    depot_capacity = ask_int("Capacità del deposito", default_depot_capacity)
```

> Se i nomi delle variabili sono leggermente diversi nel tuo file (es. `default_total`, ecc.), adatta il codice di conseguenza mantenendo l’idea: **i default arrivano da `sim_conf`**.

**Checklist**
- [ ] All’inizio di `main()` viene chiamato `load_sim_config()`
- [ ] I default usati da `ask_int(...)` arrivano dalla config YAML


---

### 3. Provare la simulazione con i nuovi default

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python -m src.sim.main_sim
```

2. Osserva i valori tra parentesi quadre quando ti vengono chiesti i parametri:
   - dovrebbero essere quelli di `conf\sim\default.yml`.

3. Premi direttamente **Invio** su tutti i parametri (per usare i default) e verifica che la simulazione:

   - giri senza errori,
   - generi il CSV in `data\raw` come prima.

**Checklist**
- [ ] I default mostrati dalla CLI coincidono con quelli di `conf\sim\default.yml`
- [ ] La simulazione gira senza errori con i nuovi default


---

### 4. (Facoltativo) Testare un ambiente alternativo via variabile d’ambiente

Se vuoi fare un piccolo esperimento in più:

1. Copia `conf\sim\default.yml` in `conf\sim\dev.yml`.
2. Modifica alcuni valori in `dev.yml` (es. `total_minutes: 60`).
3. Nel terminale (solo per quel comando), imposta la variabile d’ambiente `SIM_ENV` e avvia la simulazione.

Esempio in **PowerShell**:

```bash
$env:SIM_ENV = "dev"
python -m src.sim.main_sim
```

Oppure in **cmd**:

```bat
set SIM_ENV=dev
python -m src.sim.main_sim
```

Dovresti vedere i default aggiornati secondo `dev.yml`.

**Checklist (facoltativa)**
- [ ] Ho verificato che cambiando `SIM_ENV` vengono usati i valori di `conf\sim\dev.yml`


---

### Fine Parte 1 (Giorni 1–3)

Riepilogo di quello che hai fatto in questa Parte 1:

- [ ] Hai creato una cartella `conf/` con:
  - [ ] `conf\sim\default.yml`
  - [ ] `conf\ml\default.yml`
- [ ] Hai creato il package `src\config` con `config_loader.py`
- [ ] Puoi caricare le config tramite `load_sim_config()` e `load_ml_config()`
- [ ] La simulazione (`main_sim.py`) usa i valori di `conf\sim\default.yml` come default nella CLI
- [ ] (Facoltativo) Sei in grado di usare `SIM_ENV` per selezionare un file YAML alternativo

Quando queste caselle sono spuntate, sei pronto per la **Parte 2 della Fase 09** (`fase09_2.md`), dove:

- userai `load_ml_config()` per il training del modello,
- sistemerai `random_state` e parametri del modello per una **riproducibilità migliore**,
- salverai una piccola **scheda di report** del training accanto al modello.
