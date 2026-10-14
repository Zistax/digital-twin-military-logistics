"""Run python -m src.logistics.supply_demo: stockout -> reorder -> delivery."""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal as D

from .calendars import Calendar
from .core import Mission, MissionLine
from .operations import DepotOperations
from .roads import Network, Node, Road
from .supply import ReorderRule, SupplyWarehouse
from .warehouse import Item, Store, Vehicle


def run_demo():
    w = SupplyWarehouse(
        "supply-demo",
        [Item("goods", D(1), D(1), 30)],
        [Store("local", D(100), D(0)), Store("destination", D(100), D(0))],
        [Vehicle("van", "local", D(100), D(100))],
        network=Network(
            [Node("local", 0, 0), Node("destination", 1, 0)],
            [Road("local", "destination", 30)],
            congestion_alpha=0,
        ),
        epoch=datetime(2026, 10, 5, 6, tzinfo=timezone.utc),
        operations={
            d: DepotOperations(Calendar.daily()) for d in ("local", "destination")
        },
    )
    m = Mission(
        "supply-demo",
        "delivery",
        "local",
        "destination",
        0,
        86400,
        (MissionLine("goods", 10, D(1)),),
    )
    w.register("mission", 0, m)
    w.schedule("schedule", 0, "delivery")
    w.local_request("local", 0, "consumption", "local", {"goods": 5})
    w.configure_reorder(
        "rules", 0, {("local", "goods"): ReorderRule(D(10), D("0.5"), D(1), 43200)}
    )
    w.advance("run", 86400)
    state = w.snapshot()
    return {
        "outcome": asdict(w.outcome("delivery", 86400)),
        "supplies": state["supplies"],
        "local_request": state["local_requests"]["consumption"],
        "stock": state["stock"],
        "consumed": state["consumed"],
        "busy": state["busy"],
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
