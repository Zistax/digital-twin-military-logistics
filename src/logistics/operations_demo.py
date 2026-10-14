"""Run python -m src.logistics.operations_demo from the repository root."""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal as D

from .calendars import Calendar
from .core import Mission, MissionLine
from .operations import DepotOperations, OperationsWarehouse
from .warehouse import Item, Store, Vehicle


def run_demo():
    w = OperationsWarehouse(
        "demo",
        [Item("a", D(1), D(1), 30)],
        [Store("central", D(100), D(0)), Store("local", D(5), D(0))],
        [
            Vehicle("delivery-van", "central", D(100), D(20)),
            Vehicle("local-van", "local", D(100), D(20)),
        ],
        epoch=datetime(2026, 10, 5, 6, tzinfo=timezone.utc),
        operations={
            "central": DepotOperations(Calendar.daily(6 * 3600, 22 * 3600)),
            "local": DepotOperations(Calendar.daily(10 * 3600, 18 * 3600)),
        },
    )
    m = Mission(
        "demo",
        "delivery",
        "central",
        "local",
        0,
        8400,
        (MissionLine("a", 10, D("0.9")),),
    )
    w.receive("stock", 0, "central", {"a": 10})
    w.register("mission", 0, m)
    w.reserve("reserve", 0, "delivery")
    w.queue_loading("queue", 0, "delivery", {"trip-in": ("delivery-van", {"a": 10})})
    w.advance("load", 600)
    w.depart("depart", 600, "delivery")
    # Arrival is an input until the routing block is implemented.
    w.arrive("arrive", 3600, "trip-in")
    w.advance("first-unload", 7800)  # 10:10: five units fit; van remains busy.
    partial = asdict(w.outcome("delivery", 7800))
    outbound = Mission(
        "demo",
        "outbound",
        "local",
        "central",
        7800,
        14000,
        (MissionLine("a", 5, D(1)),),
    )
    w.register("outbound", 7800, outbound)
    w.reserve("out-reserve", 7800, "outbound")
    w.queue_loading(
        "out-queue", 7800, "outbound", {"trip-out": ("local-van", {"a": 5})}
    )
    w.advance("finish-operations", 9000)
    state = w.snapshot()
    return {
        "partial_at_10_10": partial,
        "final_at_10_30": asdict(w.outcome("delivery", 9000)),
        "waiting_seconds": state["wait_seconds"]["trip-in"],
        "destination_stock": state["stock"]["local"],
        "delivery_vehicle_free": "delivery-van" not in state["busy"],
        "delivery_vehicle_position": state["positions"]["delivery-van"],
        "operations": [
            {
                k: op[k]
                for k in ("trip_id", "kind", "depot", "start_s", "end_s", "overtime_s")
            }
            for op in state["operations"]
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
