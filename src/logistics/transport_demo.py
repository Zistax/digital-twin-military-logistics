"""Reference network, ten vehicles and a fully simulated cold-goods mission."""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal as D

from .calendars import Calendar
from .core import Mission, MissionLine
from .operations import DepotOperations
from .roads import reference_network
from .transport import TransportWarehouse
from .warehouse import Item, Store, Vehicle


def run_demo(seed=17):
    network = reference_network(seed)
    stores = [
        Store("central-a", D(1000), D(200)),
        Store("central-b", D(800), D(150)),
        Store("local-a", D(200), D(50)),
        Store("local-b", D(150), D(0)),
        Store("local-c", D(100), D(0)),
    ]
    vehicles = []
    for suffix in ("a", "b"):
        depot = "central-" + suffix
        vehicles.extend(
            [
                Vehicle("van-" + suffix, depot, D(1000), D(8)),
                Vehicle("truck-" + suffix, depot, D(8000), D(40)),
                Vehicle("cold-" + suffix, depot, D(5000), D(30), True),
            ]
        )
    vehicles.extend(
        [
            Vehicle("van-c", "local-a", D(1000), D(8)),
            Vehicle("van-d", "local-b", D(1000), D(8)),
            Vehicle("truck-c", "local-a", D(8000), D(40)),
            Vehicle("truck-d", "local-c", D(8000), D(40)),
        ]
    )
    operations = {
        "central-a": DepotOperations(
            Calendar.daily(6 * 3600, 22 * 3600), 3, D(20), D(5)
        ),
        "central-b": DepotOperations(
            Calendar.daily(6 * 3600, 22 * 3600), 3, D(20), D(5)
        ),
        "local-a": DepotOperations(
            Calendar.daily(8 * 3600, 18 * 3600, range(6)), 1, D(5), D(2)
        ),
        "local-b": DepotOperations(
            Calendar.daily(8 * 3600, 17 * 3600, range(5)), 1, D(5)
        ),
        "local-c": DepotOperations(
            Calendar.daily(8 * 3600, 17 * 3600, range(5)), 1, D(5)
        ),
    }
    w = TransportWarehouse(
        "transport-demo",
        [Item("cold-small", D(5), D("0.025"), 30, True)],
        stores,
        vehicles,
        network=network,
        operations=operations,
        epoch=datetime(2026, 10, 5, 6, tzinfo=timezone.utc),
    )
    w.receive("stock", 0, "local-a", {"cold-small": 10})
    m = Mission(
        "transport-demo",
        "mission-1",
        "local-a",
        "central-b",
        0,
        6 * 3600,
        (MissionLine("cold-small", 10, D("0.85")),),
    )
    w.register("mission", 0, m)
    w.schedule("automatic", 0, "mission-1")
    w.advance("run", 7 * 86400)
    state = w.snapshot()
    log = state["transport_log"]
    return {
        "seed": seed,
        "nodes": len(network.nodes),
        "roads": len(network.roads),
        "fleet": len(vehicles),
        "outcome": asdict(w.outcome("mission-1", 7 * 86400)),
        "empty_legs": [e for e in log if e["kind"] == "edge_enter" and e["empty"]],
        "loaded_legs": [e for e in log if e["kind"] == "edge_enter" and not e["empty"]],
        "assignments": [e for e in log if e["kind"] == "assignment"],
        "destination_stock": state["stock"]["central-b"],
        "busy_vehicles": state["busy"],
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
