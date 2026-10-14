"""Run with python -m src.logistics.demo from the repository root."""

import json
from dataclasses import asdict
from decimal import Decimal

from .core import Delivery, Mission, MissionLine, replay


def reference_case():
    mission = Mission(
        "run-reference",
        "mission-1",
        "central-a",
        "local-a",
        0,
        3600,
        (
            MissionLine("spares-small", 10, Decimal("0.9")),
            MissionLine("spares-large", 5, Decimal("0.9")),
        ),
    )
    loads = {
        ("trip-1", "batch-1", "spares-small"): 10,
        ("trip-2", "batch-2", "spares-large"): 5,
    }
    events = [
        Delivery(
            "e1",
            "run-reference",
            "mission-1",
            "trip-1",
            "batch-1",
            "spares-small",
            3000,
            3000,
            9,
        ),
        Delivery(
            "e2",
            "run-reference",
            "mission-1",
            "trip-2",
            "batch-2",
            "spares-large",
            5700,
            5700,
            5,
        ),
        Delivery(
            "e3",
            "run-reference",
            "mission-1",
            "trip-1",
            "batch-1",
            "spares-small",
            6000,
            6000,
            1,
        ),
    ]
    return mission, loads, events


if __name__ == "__main__":
    mission, loads, events = reference_case()
    print(
        json.dumps(
            {
                str(t): asdict(replay(mission, loads, events, t))
                for t in (3600, 5700, 6000)
            },
            indent=2,
        )
    )
