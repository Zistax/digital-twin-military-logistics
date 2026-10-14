from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ConvoyState(str, Enum):
    """Stati semplici per un convoglio nella simulazione."""

    EN_ROUTE = "en_route"  # in marcia verso la destinazione
    COMPLETED = "completed"  # ha completato la missione
    INCOMPLETED = "incompleted"  # non ha completato la missione


@dataclass
class Convoy:
    """Rappresenta un convoglio nella simulazione."""

    id: int
    progress: float = 0.0  # da 0.0 (partenza) a 100.0 (arrivato)
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
    queue_length: int = 0  # placeholder per una futura logica di coda
    name: Optional[str] = None
