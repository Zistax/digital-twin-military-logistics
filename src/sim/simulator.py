from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Tuple

from .config import SimConfig
from .models import Convoy, Depot, ConvoyState

from datetime import datetime
from pathlib import Path

import pandas as pd

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
            progress_increment = 100.0 * self.config.timestep_minutes / self.config.total_minutes 
        else:
            progress_increment = 100.0

        for convoy in self.convoys:
            if convoy.state == ConvoyState.EN_ROUTE:
                old_progress = convoy.progress
                convoy.progress = min(100.0, convoy.progress + progress_increment)

                # Se il convoglio ha appena completato la missione, registriamo un evento
                if old_progress < 100.0 and convoy.progress >= 100.0:
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


def run_simulation(config: SimConfig, save_to_csv: bool = True) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
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

    return all_events, summary