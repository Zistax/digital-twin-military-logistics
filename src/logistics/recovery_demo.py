"""Run python -m src.logistics.recovery_demo for an approved recovery chain."""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal as D

from .calendars import Calendar
from .core import Mission, MissionLine
from .operations import DepotOperations
from .recovery import RecoveryWarehouse
from .roads import Network, Node, Road
from .warehouse import Item, Store, Vehicle


def run_demo():
    w = RecoveryWarehouse(
        "recovery-demo",
        [Item("spares", D(1), D(1), 30)],
        [Store("origin", D(100), D(0)), Store("destination", D(100), D(0))],
        [
            Vehicle("original", "origin", D(100), D(100)),
            Vehicle("substitute", "origin", D(100), D(100)),
        ],
        network=Network(
            [Node("origin", 0, 0), Node("destination", 10, 0)],
            [Road("origin", "destination", 30)],
            congestion_alpha=0,
        ),
        epoch=datetime(2026, 10, 5, 6, tzinfo=timezone.utc),
        operations={
            d: DepotOperations(Calendar.daily(), 1, D(100))
            for d in ("origin", "destination")
        },
    )
    w.receive("stock", 0, "origin", {"spares": 20})
    m = Mission(
        "recovery-demo",
        "mission",
        "origin",
        "destination",
        0,
        2500,
        (MissionLine("spares", 10, D("0.9")),),
    )
    w.register("mission", 0, m)
    w.schedule("schedule", 0, "mission")
    w.advance("travel", 1000)
    w.damage_cargo("hidden-damage", 1000, "auto-1-0", "spares", 2)
    w.breakdown("failure", 1000, "original", False, 86400)
    w.decide("replacement-approval", 1100, "request-1", "approve")
    w.advance("first-delivery", 4100)
    first = asdict(w.outcome("mission", 4100))
    w.decide("supplement-approval", 4100, "request-2", "approve")
    w.advance("final-delivery", 7700)
    final = asdict(w.outcome("mission", 7700))
    w.advance("vehicle-restored", 87400)
    state = w.snapshot()
    return {
        "first_delivery": first,
        "final_delivery": final,
        "requests": state["requests"],
        "stock": state["stock"],
        "quarantine": state["quarantine"],
        "busy": state["busy"],
        "original_vehicle_position": state["positions"]["original"],
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
