"""Deterministic integrated example: python -m src.logistics.warehouse_demo."""

import json
from dataclasses import asdict
from decimal import Decimal as D

from .core import Delivery, Mission, MissionLine
from .warehouse import Item, Store, Vehicle, Warehouse


def run_demo():
    ledger = Warehouse(
        "run-demo",
        [Item("medium", D(10), D("0.04"), 60), Item("large", D(50), D("0.12"), 120)],
        [Store("central", D(1000), D(200)), Store("local", D(200), D(50))],
        [
            Vehicle("van", "central", D(1000), D(8)),
            Vehicle("truck", "central", D(8000), D(40)),
        ],
    )
    mission = Mission(
        "run-demo",
        "mission-1",
        "central",
        "local",
        0,
        3600,
        (MissionLine("medium", 10, D("0.9")), MissionLine("large", 5, D("0.9"))),
    )
    ledger.receive("initial-stock", 0, "central", {"medium": 10, "large": 5})
    ledger.register("create-mission", 0, mission)
    ledger.reserve("reserve-stock", 0, mission.mission_id)
    ready = ledger.start_loading(
        "start-loading",
        0,
        mission.mission_id,
        {"trip-1": ("van", {"medium": 10}), "trip-2": ("truck", {"large": 5})},
    )
    for trip, at_s in sorted(ready.items(), key=lambda p: (p[1], p[0])):
        ledger.finish_loading(f"finish-{trip}", at_s, trip)
    manifest = ledger.depart("depart", max(ready.values()), mission.mission_id)
    keys = {item: (trip, batch) for trip, batch, item in manifest}
    deliveries = []
    # Explicit external inspected events: routing/unloading are not simulated here.
    for event_id, item, quantity, at_s in [
        ("e1", "medium", 9, 3000),
        ("e2", "large", 5, 5700),
        ("e3", "medium", 1, 6000),
    ]:
        trip, batch = keys[item]
        deliveries.append(
            Delivery(
                event_id,
                "run-demo",
                "mission-1",
                trip,
                batch,
                item,
                at_s,
                at_s,
                quantity,
            )
        )
    return {
        "origin_stock_after_loading": ledger.snapshot()["stock"]["central"],
        "loading_ready_s": ready,
        "audit_commands": len(ledger.snapshot()["audit"]),
        "outcomes": {
            str(t): asdict(ledger.evaluate("mission-1", deliveries, t))
            for t in (3600, 5700, 6000)
        },
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
