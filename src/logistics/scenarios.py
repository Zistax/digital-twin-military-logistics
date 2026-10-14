"""Seeded demand plans. Requests become missions only after an observable ETA."""

from dataclasses import dataclass
from decimal import Decimal
from decimal import ROUND_CEILING
from datetime import datetime, timezone
from hashlib import sha256
from math import ceil
from random import Random

from .core import MissionLine, natural
from .warehouse import Item

THRESHOLDS = dict(
    zip(
        ("food", "cold", "medical", "spares", "electronics"),
        map(Decimal, (".8", ".85", ".95", ".9", ".75")),
    )
)
DEPOTS = ("central-a", "central-b", "local-a", "local-b", "local-c")
COLD_DEPOTS = frozenset(DEPOTS[:3])
SIZES = ("small", "medium", "large")
QUANTITIES = ((20, 100), (10, 50), (5, 25))


def reference_catalog():
    """Fifteen packaged articles, in kilograms and cubic metres."""
    measures = {
        "food": ((5, ".02"), (10, ".04"), (20, ".08")),
        "cold": ((5, ".025"), (10, ".05"), (20, ".10")),
        "medical": ((2, ".02"), (5, ".04"), (10, ".08")),
        "spares": ((10, ".025"), (25, ".06"), (50, ".12")),
        "electronics": ((3, ".03"), (10, ".10"), (25, ".25")),
    }
    return tuple(
        Item(
            f"{category}-{size}",
            Decimal(kg),
            Decimal(volume),
            handling,
            cold=category == "cold",
        )
        for category, values in measures.items()
        for size, (kg, volume), handling in zip(SIZES, values, (30, 60, 120))
    )


def stream(seed, process):
    return Random(sha256(f"scenario-v1|{seed}|{process}".encode()).digest())


@dataclass(frozen=True)
class ScenarioConfig:
    seed: int = 0
    profile: str = "regular"
    generation_days: int = 7
    extension_days: int = 7

    def __post_init__(self):
        natural(self.seed, "seed")
        natural(self.generation_days, "generation_days", True)
        natural(self.extension_days, "extension_days")
        if self.profile not in ("regular", "pressure", "perturbed"):
            raise ValueError("unknown profile")

    @property
    def generation_end_s(self):
        return self.generation_days * 86400

    @property
    def stop_s(self):
        return (self.generation_days + self.extension_days) * 86400


@dataclass(frozen=True)
class ScenarioRequest:
    request_id: str
    start_s: int
    origin_id: str
    destination_id: str
    urgent: bool
    lines: tuple[MissionLine, ...]
    deadline_kind: str
    deadline_margin: Decimal


def generate_requests(config):
    """Poisson arrivals, uniform directed pairs, independent composition and urgency.

    Regular and perturbed have identical demand for the same seed. Pressure
    changes only arrival intensity. Neither deadline nor outcomes use future
    simulation state: deadline_margin still needs an ETA at mission creation.
    """
    if not isinstance(config, ScenarioConfig):
        raise ValueError("ScenarioConfig required")
    arrivals = stream(config.seed, "arrivals")
    pairs = stream(config.seed, "pairs")
    composition = stream(config.seed, "composition")
    quantities = stream(config.seed, "quantities")
    urgency = stream(config.seed, "urgency")
    deadlines = stream(config.seed, "deadlines")
    rate = (20 if config.profile == "pressure" else 10) / 86400
    elapsed = 0.0
    result = []
    while True:
        elapsed += arrivals.expovariate(rate)
        start = ceil(elapsed)
        if start >= config.generation_end_s:
            return tuple(result)
        origin, destination = pairs.sample(DEPOTS, 2)
        eligible = [
            c for c in THRESHOLDS if c != "cold" or {origin, destination} <= COLD_DEPOTS
        ]
        categories = composition.sample(eligible, composition.randint(1, len(eligible)))
        lines = []
        for category in sorted(categories):
            formats = composition.sample(range(3), composition.randint(1, 3))
            for index in sorted(formats):
                lines.append(
                    MissionLine(
                        f"{category}-{SIZES[index]}",
                        quantities.randint(*QUANTITIES[index]),
                        THRESHOLDS[category],
                    )
                )
        draw = deadlines.random()
        kind, lo, hi = (
            ("tight", 100, 120)
            if draw < 0.3
            else ("ordinary", 130, 160) if draw < 0.8 else ("wide", 180, 220)
        )
        margin = Decimal(deadlines.randint(lo, hi)) / 100
        result.append(
            ScenarioRequest(
                f"request-{len(result)+1}",
                start,
                origin,
                destination,
                urgency.random() < 0.2,
                tuple(lines),
                kind,
                margin,
            )
        )


def expected_daily_shipping():
    """Analytical regular-profile demand, shared by initial-stock comparisons.

    Uniform nonempty category-count and format-count, uniform integer quantities.
    This is an expectation over the generator, not a lookahead at sampled demand.
    Local consumption is deliberately excluded (add its expectation separately).
    """
    demand = {
        d: {item.item_id: Decimal(0) for item in reference_catalog()} for d in DEPOTS
    }
    pair_rate = Decimal(10) / (len(DEPOTS) * (len(DEPOTS) - 1))
    for origin in DEPOTS:
        for destination in DEPOTS:
            if origin == destination:
                continue
            eligible = [
                c
                for c in THRESHOLDS
                if c != "cold" or {origin, destination} <= COLD_DEPOTS
            ]
            n = len(eligible)
            category_chance = Decimal(n + 1) / (2 * n)
            for category in eligible:
                for size, (lo, hi) in zip(SIZES, QUANTITIES):
                    demand[origin][f"{category}-{size}"] += (
                        pair_rate
                        * category_chance
                        * Decimal(2)
                        / 3
                        * Decimal(lo + hi)
                        / 2
                    )
    return demand


def expected_local_withdrawal(daily_shipping):
    """Exact expectation of ceil(U[.1,.3] * daily_shipping)."""
    if daily_shipping == 0:
        return Decimal(0)
    lo, hi = daily_shipping / 10, daily_shipping * Decimal(".3")
    return sum(
        (
            Decimal(q) * max(Decimal(0), min(hi, Decimal(q)) - max(lo, Decimal(q - 1)))
            for q in range(
                int(lo) + 1, int(hi.to_integral_value(rounding=ROUND_CEILING)) + 1
            )
        ),
        Decimal(0),
    ) / (hi - lo)


def initialize_scenario(config, epoch=None):
    """Build the reference fleet/stores and seed stocks without sampled-demand
    lookahead.

    Returns the warehouse and an explicit stock initialization ledger. Mission
    requests, external conditions and stop control are connected by a later runner.
    """
    from .calendars import Calendar
    from .incidents import IncidentPolicy
    from .operations import DepotOperations
    from .environment import EnvironmentWarehouse
    from .roads import reference_network
    from .supply import ReorderRule
    from .warehouse import Store, Vehicle

    if not isinstance(config, ScenarioConfig):
        raise ValueError("ScenarioConfig required")
    catalog = reference_catalog()
    capacities = ((1000, 200), (800, 150), (200, 50), (150, 0), (100, 0))
    stores = [Store(d, Decimal(a), Decimal(b)) for d, (a, b) in zip(DEPOTS, capacities)]
    operations = {}
    for index, depot in enumerate(DEPOTS):
        central = index < 2
        days = range(7 if central else 6 if index == 2 else 5)
        opening, closing = (6, 22) if central else (8, 18 if index == 2 else 17)
        calendar = Calendar(
            tuple((day, opening * 3600, closing * 3600) for day in days)
        )
        operations[depot] = DepotOperations(
            calendar,
            3 if central else 1,
            Decimal(20 if central else 5),
            Decimal(5 if central else 2 if index == 2 else 0),
        )
    fleet = []
    for kind, kg, volume, locations in (
        ("van", 1000, 8, DEPOTS[:4]),
        ("truck", 8000, 40, (DEPOTS[0], DEPOTS[1], DEPOTS[2], DEPOTS[4])),
        ("cold", 5000, 30, DEPOTS[:2]),
    ):
        fleet.extend(
            Vehicle(f"{kind}-{i}", d, Decimal(kg), Decimal(volume), kind == "cold")
            for i, d in enumerate(locations)
        )
    warehouse = EnvironmentWarehouse(
        f"scenario-{config.seed}-{config.profile}",
        catalog,
        stores,
        fleet,
        network=reference_network(config.seed),
        operations=operations,
        epoch=epoch or datetime(2026, 10, 5, tzinfo=timezone.utc),
        categories={item.item_id: item.item_id.split("-")[0] for item in catalog},
        incident_policy=IncidentPolicy(config.seed, config.profile, True, True),
    )
    shipping = expected_daily_shipping()
    ledger, rules = [], {}
    for store in stores:
        depot = store.depot_id
        central = depot.startswith("central")
        free = {False: store.ordinary_m3, True: store.cold_m3}
        quantities = {}
        for item in catalog:
            daily = shipping[depot][item.item_id]
            if not daily:
                continue
            total = daily + expected_local_withdrawal(daily)
            wanted = int(
                (total * (3 if central else 1)).to_integral_value(
                    rounding=ROUND_CEILING
                )
            )
            quantity = min(wanted, int(free[item.cold] // item.m3))
            free[item.cold] -= item.m3 * quantity
            if quantity:
                quantities[item.item_id] = quantity
            ledger.append(
                {
                    "depot": depot,
                    "item": item.item_id,
                    "daily_demand": total,
                    "wanted": wanted,
                    "initialized": quantity,
                    "capacity_limited": quantity < wanted,
                }
            )
            rules[(depot, item.item_id)] = ReorderRule(
                total,
                Decimal("1.5" if central else ".5"),
                Decimal(3 if central else 1),
                86400 if central else 43200,
            )
        warehouse.receive(f"initial:{depot}", 0, depot, quantities)
        warehouse.schedule_local_days(
            f"local:{depot}",
            0,
            depot,
            shipping[depot],
            config.generation_days + config.extension_days,
            config.seed,
        )
    warehouse.configure_reorder("reorder-config", 0, rules)
    return warehouse, tuple(ledger)
