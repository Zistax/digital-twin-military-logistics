# Fase 02 – Simulatore base (Windows, dettaglio per giornate)

> **Scopo della Fase 02**  
> Creare il **primo simulatore semplice** di convogli, con:
> - una piccola configurazione (`SimConfig`),
> - modelli base (`Convoy`, `Depot`),
> - un ciclo di simulazione a passi,
> - un log di eventi in memoria,
> - salvataggio dei log in un file CSV in `data\raw`,
> - un aggiornamento di `main_sim.py` per lanciare la simulazione da riga di comando.

La fase è pensata per circa **8 giornate di lavoro** da ~2 ore ciascuna.  
Se ti serve più tempo per un giorno, **non è un problema**: continua al giorno successivo.

Prima di iniziare, verifica di aver completato la **Fase 01** (cartelle, ambiente `.venv`, `main_sim.py` di prova, `pytest`, `run_checks.bat`).

Struttura della Fase 02:

- Giorno 1 – Creare la configurazione di simulazione (`SimConfig`)
- Giorno 2 – Definire i modelli di dominio (`Convoy`, `Depot`, stati)
- Giorno 3 – Creare la struttura del simulatore (`SimState`, ciclo a passi)
- Giorno 4 – Aggiungere logging degli eventi in memoria
- Giorno 5 – Salvare il log in CSV in `data\raw`
- Giorno 6 – Interfaccia da riga di comando in `main_sim.py` (scegli parametri)
- Giorno 7 – Creare test automatici per il simulatore
- Giorno 8 – Esecuzione completa, aggiornamento `run_checks.bat` (se serve) e commit Git

---

## Giorno 1 – Creare la configurazione di simulazione (`SimConfig`)

### Obiettivo del giorno
Aggiungere un **modulo di configurazione** (`config.py`) per definire i parametri base della simulazione.

Userai:
- `dataclasses` (una funzionalità di Python per definire “contenitori di dati” semplici).

---

### 1. Attivare l’ambiente virtuale e aprire il progetto

1. Apri **PowerShell** o **cmd**.
2. Vai nella cartella del progetto (sostituisci `TUO_UTENTE` con il tuo utente Windows):

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

4. Verifica che vedi `(.venv)` all’inizio della riga del terminale.

**Checklist**
- [ ] Sono nella cartella `digital-twin-logistico`
- [ ] L’ambiente `.venv` è attivo (`(.venv)` nel prompt)

---

### 2. Creare il file `config.py`

1. Apri **VS Code** e assicurati che la cartella `digital-twin-logistico` sia aperta.
2. Nella barra laterale, espandi la cartella `src` → `sim`.
3. Crea un nuovo file chiamato `config.py` dentro `src\sim`.
4. Inserisci il seguente contenuto:

```python
from dataclasses import dataclass


@dataclass
class SimConfig:
    """
    Configurazione di base per una simulazione.

    Per ora contiene solo pochi parametri, ma potrai estenderla in futuro.
    """

    simulation_name: str = "demo"
    total_minutes: int = 120          # Durata della simulazione in minuti
    timestep_minutes: int = 10        # Durata di ogni passo di simulazione in minuti
    n_convoys: int = 5                # Numero di convogli simulati
    depot_capacity: int = 2           # Capacità semplice del deposito (placeholder)
```

5. Salva il file (`Ctrl + S`).

**Checklist**
- [ ] Esiste il file `src\sim\config.py`
- [ ] Il file contiene la classe `SimConfig` con i campi indicati

---

### 3. Aggiornare `main_sim.py` per usare `SimConfig` (senza cambiare il comportamento)

Per ora non cambieremo il comportamento dello script, ma lo prepariamo per usare `SimConfig`.

1. Apri il file `src\sim\main_sim.py` in VS Code.
2. Sostituisci **interamente** il contenuto con questo (più completo):

```python
"""
Modulo principale del simulatore (versione semplice, Windows).

In questa fase:
- definiamo un punto di ingresso main()
- creiamo una SimConfig con valori di default
- stampiamo a schermo la configurazione

Nelle fasi successive, main() lancerà una vera simulazione.
"""

from .config import SimConfig


def main() -> None:
    """Punto di ingresso principale per il simulatore."""
    print("=== Simulatore logistico – Fase 02 (base) ===")

    # Creiamo una configurazione di default
    config = SimConfig()

    print("Configurazione corrente:")
    print(f"  Nome simulazione:   {config.simulation_name}")
    print(f"  Durata totale:      {config.total_minutes} minuti")
    print(f"  Timestep:           {config.timestep_minutes} minuti")
    print(f"  Numero convogli:    {config.n_convoys}")
    print(f"  Capacità deposito:  {config.depot_capacity}")

    print()
    print("Per il momento la simulazione non fa ancora nulla di complesso.")
    print("Nei prossimi giorni aggiungerai i modelli e la logica di simulazione.")


if __name__ == "__main__":
    main()
```

3. Salva il file.

---

### 4. Eseguire il simulatore per verificare

Nel terminale (con `.venv` attivo), esegui:

```bash
python -m src.sim.main_sim
```

oppure:

```bash
py -m src.sim.main_sim
```

Dovresti vedere il testo con la configurazione stampata.

**Checklist (fine Giorno 1)**
- [ ] `src\sim\config.py` creato
- [ ] `main_sim.py` aggiornato con uso di `SimConfig`
- [ ] Il comando `python -m src.sim.main_sim` (o `py ...`) funziona e mostra la configurazione

---

## Giorno 2 – Definire i modelli di dominio (`Convoy`, `Depot`, stati)

### Obiettivo del giorno
Creare i **modelli di dominio** principali:
- `Convoy` (convoglio)
- `Depot` (deposito)
- `ConvoyState` (stato del convoglio)

Questo ti permetterà di avere oggetti chiari da gestire nella simulazione.

---

### 1. Creare il file `models.py`

1. In VS Code, sotto `src\sim`, crea un nuovo file chiamato `models.py`.
2. Inserisci il seguente contenuto:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ConvoyState(str, Enum):
    """Stati semplici per un convoglio nella simulazione."""

    EN_ROUTE = "en_route"      # in marcia verso la destinazione
    COMPLETED = "completed"    # ha completato la missione


@dataclass
class Convoy:
    """Rappresenta un convoglio nella simulazione."""

    id: int
    progress: float = 0.0          # da 0.0 (partenza) a 1.0 (arrivato)
    state: ConvoyState = ConvoyState.EN_ROUTE

    def is_completed(self) -> bool:
        """Ritorna True se il convoglio ha completato la missione."""
        return self.state == ConvoyState.COMPLETED


@dataclass
class Depot:
    """Rappresenta un deposito molto semplificato.

    In questa fase è quasi un placeholder per il futuro.
    """

    id: int
    capacity: int
    queue_length: int = 0            # placeholder per una futura logica di coda
    name: Optional[str] = None
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\sim\models.py`
- [ ] Dentro sono definiti `ConvoyState`, `Convoy`, `Depot`

---

### 2. (Opzionale) Breve test manuale in Python REPL

Non è obbligatorio, ma può aiutarti a prendere confidenza.

1. Nel terminale (con `.venv` attivo), avvia Python interattivo:

```bash
python
```

2. Prova a digitare:

```python
from src.sim.models import Convoy, ConvoyState

c = Convoy(id=1)
print(c)
print(c.state == ConvoyState.EN_ROUTE)
print(c.is_completed())
```

Dovresti vedere qualcosa come: convoglio con `progress=0.0`, stato `EN_ROUTE`, e `is_completed()` che restituisce `False`.

3. Per uscire dal REPL, digita:

```python
exit()
```

**Checklist (fine Giorno 2)**
- [ ] `Convoy`, `Depot` e `ConvoyState` sono definiti
- [ ] (Opzionale) Ho fatto una prova veloce nel REPL

---

## Giorno 3 – Creare la struttura del simulatore (`SimState`, ciclo a passi)

### Obiettivo del giorno
Creare un file `simulator.py` che contenga:
- una classe `SimState` per tenere lo stato della simulazione,
- un metodo `step()` che esegue un passo di simulazione,
- una funzione `run_simulation()` che lancia il ciclo di simulazione.

In questa fase non simuleremo ancora eventi complessi, ma solo il **progresso dei convogli** da 0.0 a 1.0.

---

### 1. Creare il file `simulator.py`

1. In VS Code, dentro `src\sim`, crea il file `simulator.py`.
2. Inserisci il seguente contenuto:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Tuple

from .config import SimConfig
from .models import Convoy, Depot, ConvoyState


@dataclass
class SimState:
    """Stato della simulazione.

    Questa classe tiene traccia del tempo corrente, dei convogli e del deposito.
    """

    config: SimConfig
    current_minute: int = 0
    convoys: List[Convoy] = field(default_factory=list)
    depot: Depot | None = None

    def __post_init__(self) -> None:
        # Inizializza il deposito se non è stato passato
        if self.depot is None:
            self.depot = Depot(id=1, capacity=self.config.depot_capacity, name="Main Depot")

        # Inizializza i convogli se la lista è vuota
        if not self.convoys:
            for i in range(1, self.config.n_convoys + 1):
                self.convoys.append(Convoy(id=i))

    def step(self) -> List[Dict[str, object]]:
        """Esegue un singolo passo di simulazione.

        Ritorna una lista di 'eventi' (dizionari) che descrivono cosa è successo nel passo.
        In questa fase consideriamo solo il completamento dei convogli.
        """
        events: List[Dict[str, object]] = []

        # Avanza il tempo
        self.current_minute += self.config.timestep_minutes

        # Calcoliamo di quanto avanza il 'progress' a ogni passo
        if self.config.total_minutes > 0:
            progress_increment = self.config.timestep_minutes / self.config.total_minutes
        else:
            progress_increment = 1.0

        for convoy in self.convoys:
            if convoy.state == ConvoyState.EN_ROUTE:
                old_progress = convoy.progress
                convoy.progress = min(1.0, convoy.progress + progress_increment)

                # Se il convoglio ha appena completato la missione, registriamo un evento
                if old_progress < 1.0 and convoy.progress >= 1.0:
                    convoy.state = ConvoyState.COMPLETED
                    events.append(
                        {
                            "event_type": "convoy_completed",
                            "convoy_id": convoy.id,
                            "minute": self.current_minute,
                            "progress": convoy.progress,
                        }
                    )

        return events


def run_simulation(config: SimConfig) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    """Lancia una simulazione completa con la configurazione indicata.

    Ritorna una tupla (events, summary):
    - events: lista di eventi (in questa fase, completamenti dei convogli)
    - summary: dizionario con qualche metrica riassuntiva
    """
    state = SimState(config=config)
    all_events: List[Dict[str, object]] = []

    # Numero di passi di simulazione (es. total_minutes=120, timestep=10 -> 12 passi)
    if config.timestep_minutes <= 0:
        raise ValueError("timestep_minutes deve essere > 0")

    n_steps = config.total_minutes // config.timestep_minutes

    for step_index in range(n_steps):
        step_events = state.step()

        # Aggiungiamo l'indice del passo agli eventi
        for event in step_events:
            event["step_index"] = step_index
            all_events.append(event)

    # Calcoliamo un piccolo riassunto
    n_completed = sum(1 for c in state.convoys if c.state == ConvoyState.COMPLETED)
    n_total = len(state.convoys)

    summary: Dict[str, object] = {
        "simulation_name": config.simulation_name,
        "total_minutes": config.total_minutes,
        "timestep_minutes": config.timestep_minutes,
        "n_convoys": n_total,
        "n_completed_convoys": n_completed,
        "n_not_completed_convoys": n_total - n_completed,
        "final_minute": state.current_minute,
    }

    return all_events, summary
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\sim\simulator.py`
- [ ] Dentro sono definiti `SimState` e `run_simulation`

---

### 2. Modificare `main_sim.py` per lanciare una simulazione di prova

1. Apri `src\sim\main_sim.py`.
2. Sostituisci **tutto** il contenuto con il seguente:

```python
"""
Punto di ingresso principale del simulatore (Fase 02).

In questa versione:
- crea una configurazione SimConfig di base
- esegue la simulazione con run_simulation
- stampa un piccolo riassunto
"""

from .config import SimConfig
from .simulator import run_simulation


def main() -> None:
    print("=== Simulatore logistico – Fase 02 (simulatore base) ===")

    config = SimConfig()
    print("Eseguo la simulazione con la configurazione di default...")
    print(f"  Durata totale:     {config.total_minutes} minuti")
    print(f"  Timestep:          {config.timestep_minutes} minuti")
    print(f"  Numero convogli:   {config.n_convoys}")
    print(f"  Capacità deposito: {config.depot_capacity}")
    print()

    events, summary = run_simulation(config)

    print("=== Risultati simulazione ===")
    print(f"Nome simulazione:          {summary['simulation_name']}")
    print(f"Minuto finale simulazione: {summary['final_minute']}")
    print(f"Convogli totali:           {summary['n_convoys']}")
    print(f"Convogli completati:       {summary['n_completed_convoys']}")
    print(f"Convogli non completati:   {summary['n_not_completed_convoys']}")
    print()
    print(f"Numero di eventi registrati: {len(events)}")
    print("Nei prossimi giorni aggiungerai logging su file e parametri personalizzabili.")


if __name__ == "__main__":
    main()
```

3. Salva il file.

---

### 3. Eseguire la simulazione di prova

Nel terminale (con `.venv` attivo), esegui:

```bash
python -m src.sim.main_sim
```

Dovresti vedere un riassunto della simulazione (convogli tutti completati se il tempo totale è sufficiente).

**Checklist (fine Giorno 3)**
- [ ] `simulator.py` creato con `SimState` e `run_simulation`
- [ ] `main_sim.py` aggiornato per usare `run_simulation`
- [ ] `python -m src.sim.main_sim` funziona e mostra un riassunto

---

## Giorno 4 – Aggiungere logging degli eventi in memoria (struttura più ricca)

### Obiettivo del giorno
Arricchire un po’ la struttura degli eventi generati da `run_simulation`, in modo che siano pronti per essere salvati su file nella giornata successiva.

In pratica:
- definiamo meglio cosa contiene ogni evento,
- aggiungiamo un tipo di evento iniziale di “spawn” (creazione convogli).

---

### 1. Aggiornare `SimState` per creare eventi di spawn

1. Apri `src\sim\simulator.py`.
2. Cerca il metodo `__post_init__` e modificalo così:

```python
    def __post_init__(self) -> None:
        # Inizializza il deposito se non è stato passato
        if self.depot is None:
            self.depot = Depot(id=1, capacity=self.config.depot_capacity, name="Main Depot")

        # Inizializza i convogli se la lista è vuota
        if not self.convoys:
            for i in range(1, self.config.n_convoys + 1):
                self.convoys.append(Convoy(id=i))
```

In questa fase non generiamo ancora eventi di spawn qui, ma li aggiungeremo in `run_simulation`.

---

### 2. Creare eventi di tipo "convoy_spawned" all’inizio

Sempre in `simulator.py`, aggiorna la funzione `run_simulation` così:

1. Sostituisci l’inizio della funzione con questa versione, che crea eventi iniziali di spawn:

```python
def run_simulation(config: SimConfig) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    """Lancia una simulazione completa con la configurazione indicata.

    Ritorna una tupla (events, summary):
    - events: lista di eventi (in questa fase, spawn e completamenti dei convogli)
    - summary: dizionario con qualche metrica riassuntiva
    """
    state = SimState(config=config)
    all_events: List[Dict[str, object]] = []

    # Eventi iniziali di "spawn" per ogni convoglio
    for convoy in state.convoys:
        all_events.append(
            {
                "event_type": "convoy_spawned",
                "convoy_id": convoy.id,
                "minute": 0,
                "step_index": -1,
                "progress": convoy.progress,
            }
        )

    # Numero di passi di simulazione (es. total_minutes=120, timestep=10 -> 12 passi)
    if config.timestep_minutes <= 0:
        raise ValueError("timestep_minutes deve essere > 0")

    n_steps = config.total_minutes // config.timestep_minutes

    for step_index in range(n_steps):
        step_events = state.step()

        # Aggiungiamo l'indice del passo agli eventi
        for event in step_events:
            event["step_index"] = step_index
            all_events.append(event)
```

2. La parte successiva della funzione (`# Calcoliamo un piccolo riassunto`) può rimanere come prima.

**Checklist**
- [ ] `run_simulation` ora aggiunge eventi di tipo `"convoy_spawned"` all’inizio
- [ ] Gli eventi di completamento hanno i campi `event_type`, `convoy_id`, `minute`, `step_index`, `progress`

---

### 3. Prova rapida di esecuzione

Nel terminale, esegui:

```bash
python -m src.sim.main_sim
```

Non vedrai ancora i dettagli degli eventi a schermo, ma il comportamento generale non dovrebbe dare errori.

**Checklist (fine Giorno 4)**
- [ ] `python -m src.sim.main_sim` gira senza errori dopo le modifiche
- [ ] `run_simulation` restituisce una lista di eventi con struttura più ricca (lo verificherai meglio domani)

---

## Giorno 5 – Salvare il log degli eventi in CSV (`data\raw`)

### Obiettivo del giorno
Usare **pandas** per salvare la lista di eventi in un file CSV in `data\raw`, con un nome che include data e ora.

---

### 1. Aggiornare `run_simulation` per salvare su CSV

1. Apri `src\sim\simulator.py`.
2. In cima al file, aggiungi i seguenti import se non ci sono già:

```python
from datetime import datetime
from pathlib import Path

import pandas as pd
```

3. Modifica la firma della funzione `run_simulation` per aggiungere un parametro `save_to_csv` (con default True):

```python
def run_simulation(config: SimConfig, save_to_csv: bool = True) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
```

4. Alla fine della funzione, **prima** del `return all_events, summary`, aggiungi questo blocco:

```python
    # Se richiesto, salviamo gli eventi in un file CSV
    if save_to_csv:
        # Creiamo la cartella data/raw se non esiste
        output_dir = Path("data") / "raw"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Nome file con timestamp (es. sim_events_20250101_153000.csv)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = output_dir / f"sim_events_{timestamp}.csv"

        df = pd.DataFrame(all_events)
        df.to_csv(csv_path, index=False)

        # Aggiungiamo il percorso del file al summary
        summary["events_csv_path"] = str(csv_path)
```

5. Verifica che la funzione `run_simulation` ora:

- accetta `save_to_csv: bool = True`,
- crea la cartella `data\raw` se non esiste,
- salva un CSV con gli eventi,
- scrive il percorso nel `summary`.

**Checklist**
- [ ] `simulator.py` importa `datetime`, `Path`, `pandas as pd`
- [ ] `run_simulation` ha il parametro `save_to_csv`
- [ ] Esiste il blocco che salva gli eventi in CSV in `data\raw`

---

### 2. Aggiornare `main_sim.py` per mostrare il percorso del CSV

1. Apri `src\sim\main_sim.py`.
2. Sostituisci la funzione `main()` con questa versione (puoi sostituire solo la funzione, mantenendo imports e if `__name__`):

```python
def main() -> None:
    print("=== Simulatore logistico – Fase 02 (simulatore base) ===")

    config = SimConfig()
    print("Eseguo la simulazione con la configurazione di default...")
    print(f"  Durata totale:     {config.total_minutes} minuti")
    print(f"  Timestep:          {config.timestep_minutes} minuti")
    print(f"  Numero convogli:   {config.n_convoys}")
    print(f"  Capacità deposito: {config.depot_capacity}")
    print()

    events, summary = run_simulation(config, save_to_csv=True)

    print("=== Risultati simulazione ===")
    print(f"Nome simulazione:          {summary['simulation_name']}")
    print(f"Minuto finale simulazione: {summary['final_minute']}")
    print(f"Convogli totali:           {summary['n_convoys']}")
    print(f"Convogli completati:       {summary['n_completed_convoys']}")
    print(f"Convogli non completati:   {summary['n_not_completed_convoys']}")
    print(f"Eventi registrati:         {len(events)}")

    csv_path = summary.get("events_csv_path")
    if csv_path:
        print()
        print(f"Log eventi salvato in: {csv_path}")

    print()
    print("Nei prossimi passi aggiungerai parametri personalizzabili e test automatici.")
```

3. Salva il file.

---

### 3. Eseguire la simulazione e controllare il CSV

Nel terminale (con `.venv` attivo), esegui:

```bash
python -m src.sim.main_sim
```

Dovresti vedere, oltre ai risultati, una riga tipo:

```text
Log eventi salvato in: data\raw\sim_events_2025XXXX_XXXXXX.csv
```

Apri Esplora File e verifica che il file esista:
- vai in `C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico\data\raw`
- dovresti vedere il file `sim_events_...csv`

**Checklist (fine Giorno 5)**
- [ ] `python -m src.sim.main_sim` esegue la simulazione e mostra il percorso del CSV
- [ ] Esiste un file `sim_events_YYYYMMDD_HHMMSS.csv` in `data\raw`
- [ ] Il file CSV si apre (anche con Blocco Note o Excel) e contiene righe di eventi

---

## Giorno 6 – Parametri da input utente (configurazione base da console)

### Obiettivo del giorno
Permettere di scegliere alcuni parametri da riga di comando:
- numero di convogli,
- durata totale della simulazione,
- timestep.

Con valori di default nel caso l’utente premi solo **Invio**.

---

### 1. Aggiungere una funzione di input sicuro in `main_sim.py`

1. Apri `src\sim\main_sim.py`.
2. Subito dopo gli import, aggiungi questa funzione di supporto:

```python
def ask_int(
    prompt: str,
    default: int,
) -> int:
    """Chiede un intero all'utente con un valore di default.

    Se l'utente preme solo Invio oppure inserisce un valore non valido,
    viene restituito il valore di default.
    """
    full_prompt = f"{prompt} [{default}]: "

    user_input = input(full_prompt).strip()
    if user_input == "":
        return default

    try:
        value = int(user_input)
    except ValueError:
        print(f"Valore non valido, uso il default: {default}")
        return default

    if value <= 0:
        print(f"Il valore deve essere > 0. Uso il default: {default}")
        return default

    return value
```

3. Salva il file.

---

### 2. Aggiornare `main()` per usare i valori richiesti all’utente

Sostituisci la funzione `main()` con questa versione:

```python
def main() -> None:
    print("=== Simulatore logistico – Fase 02 (simulatore base, parametri da console) ===")
    print("Premi Invio per accettare i valori di default indicati tra parentesi quadre.")
    print()

    default_config = SimConfig()

    total_minutes = ask_int("Durata totale simulazione (minuti)", default_config.total_minutes)
    timestep_minutes = ask_int("Durata di ogni passo (minuti)", default_config.timestep_minutes)
    n_convoys = ask_int("Numero di convogli", default_config.n_convoys)
    depot_capacity = ask_int("Capacità del deposito (placeholder)", default_config.depot_capacity)

    # Creiamo una nuova configurazione con i valori scelti
    config = SimConfig(
        simulation_name="console_run",
        total_minutes=total_minutes,
        timestep_minutes=timestep_minutes,
        n_convoys=n_convoys,
        depot_capacity=depot_capacity,
    )

    print()
    print("Eseguo la simulazione con la seguente configurazione:")
    print(f"  Durata totale:     {config.total_minutes} minuti")
    print(f"  Timestep:          {config.timestep_minutes} minuti")
    print(f"  Numero convogli:   {config.n_convoys}")
    print(f"  Capacità deposito: {config.depot_capacity}")
    print()

    events, summary = run_simulation(config, save_to_csv=True)

    print("=== Risultati simulazione ===")
    print(f"Nome simulazione:          {summary['simulation_name']}")
    print(f"Minuto finale simulazione: {summary['final_minute']}")
    print(f"Convogli totali:           {summary['n_convoys']}")
    print(f"Convogli completati:       {summary['n_completed_convoys']}")
    print(f"Convogli non completati:   {summary['n_not_completed_convoys']}")
    print(f"Eventi registrati:         {len(events)}")

    csv_path = summary.get("events_csv_path")
    if csv_path:
        print()
        print(f"Log eventi salvato in: {csv_path}")

    print()
    print("Fase 02: ora puoi lanciare simulazioni cambiando i parametri direttamente dalla console.")
```

3. Salva il file.

---

### 3. Provare la simulazione con parametri diversi

Nel terminale (con `.venv` attivo), esegui:

```bash
python -m src.sim.main_sim
```

- Prova a inserire alcuni valori (es. 60 minuti, timestep 5, 3 convogli).
- Prova anche a premere solo **Invio** per usare i default.
- Prova a mettere un valore non valido (es. testo) e verifica che venga usato il default.

**Checklist (fine Giorno 6)**
- [ ] `main_sim.py` chiede i parametri da console
- [ ] Posso eseguire la simulazione con diversi parametri
- [ ] I CSV in `data\raw` vengono creati ad ogni esecuzione

---

## Giorno 7 – Test automatici per il simulatore

### Obiettivo del giorno
Aggiungere test automatici per verificare che `run_simulation` funzioni come previsto per alcune configurazioni semplici.

---

### 1. Creare il file di test `tests\test_simulator_basic.py`

1. In VS Code, nella cartella `tests`, crea un file chiamato `test_simulator_basic.py`.
2. Inserisci il seguente contenuto:

```python
from src.sim.config import SimConfig
from src.sim.simulator import run_simulation


def test_run_simulation_basic():
    """Verifica che la simulazione base giri senza errori e produca eventi."""
    config = SimConfig(
        simulation_name="test_run",
        total_minutes=60,
        timestep_minutes=10,
        n_convoys=3,
        depot_capacity=2,
    )

    events, summary = run_simulation(config, save_to_csv=False)

    # Dovrebbe esserci almeno un evento per convoglio (spawn)
    assert len(events) >= config.n_convoys

    # Verifichiamo che il numero di convogli nel summary sia consistente
    assert summary["n_convoys"] == config.n_convoys

    # In questo setup, tutti i convogli dovrebbero completare la missione
    assert summary["n_not_completed_convoys"] == 0
```

3. Salva il file.

---

### 2. Eseguire i test con `pytest`

Nel terminale (con `.venv` attivo), esegui:

```bash
pytest
```

Dovresti vedere qualcosa come:

```text
============================= test session starts =============================
collected X items

tests/test_dummy.py ........
tests/test_simulator_basic.py .

============================== X passed in 0.XXs ==============================
```

(se hai solo i due test, vedrai 2 test passati).

**Checklist (fine Giorno 7)**
- [ ] Esiste `tests\test_simulator_basic.py`
- [ ] `pytest` gira senza errori
- [ ] Il test `test_run_simulation_basic` passa

---

## Giorno 8 – Esecuzione completa, `run_checks.bat` e commit Git

### Obiettivo del giorno
- Verificare che tutto il flusso funzioni (`run_checks.bat` → test + simulazione),
- Fare un commit Git con la Fase 02 completata.

---

### 1. (Opzionale) Aggiornare il messaggio di `run_checks.bat`

Apri il file `run_checks.bat` nella radice del progetto e, se vuoi, aggiorna i messaggi per riflettere che ora ci sono anche test del simulatore.  
Ad esempio, puoi lasciare il contenuto come già definito in Fase 01 o modificarlo leggermente nei testi, ma **non è obbligatorio**.

L’importante è che:
- attivi `.venv`,
- lanci `pytest`,
- lanci `python -m src.sim.main_sim`.

**Checklist**
- [ ] `run_checks.bat` esiste e contiene i comandi per attivare `.venv`, eseguire `pytest`, eseguire `python -m src.sim.main_sim`

---

### 2. Lanciare `run_checks.bat`

1. In Esplora File, fai doppio clic su `run_checks.bat`
   - oppure, dal terminale (anche senza `.venv` attivo):

   ```bash
   run_checks.bat
   ```

2. Verifica che:
   - l’ambiente virtuale venga attivato,
   - `pytest` giri e i test passino,
   - la simulazione venga eseguita chiedendo i parametri da console.

**Checklist**
- [ ] `run_checks.bat` gira senza errori
- [ ] I test passano
- [ ] La simulazione parte al termine dei test

---

### 3. Commit Git della Fase 02

Nel terminale, dentro `digital-twin-logistico` (non serve ambiente attivo per Git):

1. Controlla lo stato:

```bash
git status
```

2. Aggiungi i file nuovi e modificati:

```bash
git add .
```

3. Crea un commit con un messaggio chiaro, ad esempio:

```bash
git commit -m "Fase 02: simulatore base con logging eventi e CSV"
```

4. Controlla di nuovo lo stato:

```bash
git status
```

Dovresti vedere:
- `nothing to commit, working tree clean`

**Checklist (fine Giorno 8)**
- [ ] `run_checks.bat` funziona
- [ ] I test `pytest` passano
- [ ] Posso lanciare `python -m src.sim.main_sim` e ottenere un CSV
- [ ] Ho fatto il commit Git `"Fase 02: simulatore base con logging eventi e CSV"`

---

## Fine Fase 02 – Criteri di completamento

La Fase 02 è completata quando:

- [ ] Esistono i file:
  - `src\sim\config.py`
  - `src\sim\models.py`
  - `src\sim\simulator.py`
  - `src\sim\main_sim.py` (aggiornato)
- [ ] `run_simulation` esegue una simulazione a passi (tempo in minuti, convogli con progress)
- [ ] Viene generata una lista di eventi con campi: `event_type`, `convoy_id`, `minute`, `step_index`, `progress`
- [ ] Gli eventi vengono salvati in un CSV in `data\raw`
- [ ] Posso scegliere numero convogli, durata e timestep da console
- [ ] Esiste il test `tests\test_simulator_basic.py` e `pytest` passa
- [ ] `run_checks.bat` esegue test + simulazione senza errori
- [ ] Ho fatto un commit Git dedicato alla Fase 02

Quando tutte queste caselle sono spuntate, sei pronto per la **Fase 03**, dove inizierai a lavorare su **log più strutturati e prime metriche/KPI** a partire dai CSV generati.
