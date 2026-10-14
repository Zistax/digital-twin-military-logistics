from dataclasses import dataclass


@dataclass
class SimConfig:
    """
    Configurazione di base per una simulazione.

    Per ora contiene solo pochi parametri, ma potrai estenderla in futuro.
    """

    simulation_name: str = "demo"
    total_minutes: int = 120  # Durata della simulazione in minuti
    timestep_minutes: int = 10  # Durata di ogni passo di simulazione in minuti
    n_convoys: int = 5  # Numero di convogli simulati
    depot_capacity: int = 2

    def __post_init__(self):
        if (
            not isinstance(self.simulation_name, str)
            or not self.simulation_name.strip()
        ):
            raise ValueError("simulation_name must be nonempty")
        for field in (
            "total_minutes",
            "timestep_minutes",
            "n_convoys",
            "depot_capacity",
        ):
            value = getattr(self, field)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{field} must be a positive integer")
