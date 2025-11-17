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
    depot_capacity: int = 2     