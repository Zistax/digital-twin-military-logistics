"""Transactional stock, reservations and manual loading plans.

Public commands require an idempotency key and monotonic simulated seconds.
This module owns loading, not calendars, routing or unloading scheduling.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal
from functools import wraps

from .core import Delivery, Mission, identifier, natural, replay


def measure(value, name, positive=False):
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
        or (positive and value == 0)
    ):
        bound = "positive" if positive else "nonnegative"
        raise ValueError(f"{name}: finite {bound} Decimal")


@dataclass(frozen=True)
class Item:
    item_id: str
    kg: Decimal
    m3: Decimal
    handling_s: int
    cold: bool = False
    cold_compatible: bool = True
    cold_tolerance_s: int | None = None

    def __post_init__(self):
        identifier(self.item_id)
        measure(self.kg, "kg", True)
        measure(self.m3, "m3", True)
        natural(self.handling_s, "handling_s", True)
        if type(self.cold) is not bool or type(self.cold_compatible) is not bool:
            raise ValueError("compatibility flags must be booleans")
        if self.cold and not self.cold_compatible:
            raise ValueError("cold item must be cold compatible")
        if self.cold_tolerance_s is not None:
            natural(self.cold_tolerance_s, "cold_tolerance_s")
            if not self.cold:
                raise ValueError("cold tolerance requires a cold item")


@dataclass(frozen=True)
class Store:
    depot_id: str
    ordinary_m3: Decimal
    cold_m3: Decimal

    def __post_init__(self):
        identifier(self.depot_id)
        measure(self.ordinary_m3, "ordinary_m3")
        measure(self.cold_m3, "cold_m3")


@dataclass(frozen=True)
class Vehicle:
    vehicle_id: str
    depot_id: str
    max_kg: Decimal
    max_m3: Decimal
    cold: bool = False

    def __post_init__(self):
        identifier(self.vehicle_id)
        identifier(self.depot_id)
        measure(self.max_kg, "max_kg", True)
        measure(self.max_m3, "max_m3", True)
        if type(self.cold) is not bool:
            raise ValueError("cold must be boolean")


@dataclass
class Job:
    mission: Mission
    urgent: bool
    order: int
    reserved: dict = field(default_factory=dict)
    status: str = "waiting"


@dataclass
class Load:
    mission_id: str
    vehicle_id: str
    quantities: dict
    started_s: int
    ready_s: int
    status: str = "loading"


def command(function):
    """Rollback on rejection; exact retries return the original response."""

    @wraps(function)
    def wrapper(self, command_id, at_s, *args, **kwargs):
        identifier(command_id)
        natural(at_s, "at_s")
        signature = deepcopy((function.__name__, at_s, args, kwargs))
        if command_id in self._commands:
            old_signature, result = self._commands[command_id]
            if old_signature != signature:
                raise ValueError("conflicting command retry")
            return deepcopy(result)
        if at_s < self._clock:
            raise ValueError("commands must be chronological")
        previous = deepcopy(self.__dict__)
        try:
            self._before_command(at_s)
            result = function(self, command_id, at_s, *args, **kwargs)
            self._check()
            self._clock = at_s
            if hasattr(self, "_journal"):
                self._journal.capture(self, at_s)
            self._audit.append(
                {
                    "command_id": command_id,
                    "at_s": at_s,
                    "operation": function.__name__,
                    "arguments": deepcopy(args),
                    "options": deepcopy(kwargs),
                    "result": deepcopy(result),
                }
            )
            self._commands[command_id] = (signature, deepcopy(result))
            return deepcopy(result)
        except Exception:
            self.__dict__ = previous
            raise

    return wrapper


class Warehouse:
    def __init__(self, simulation_id, items, stores, vehicles, tick_s=300):
        identifier(simulation_id)
        natural(tick_s, "tick_s", True)
        self.simulation_id = simulation_id
        self.tick_s = tick_s
        self._items = self._index(items, Item, "item_id")
        self._stores = self._index(stores, Store, "depot_id")
        self._vehicles = self._index(vehicles, Vehicle, "vehicle_id")
        if any(v.depot_id not in self._stores for v in self._vehicles.values()):
            raise ValueError("unknown vehicle depot")
        self._positions = {k: v.depot_id for k, v in self._vehicles.items()}
        self._stock = {k: {} for k in self._stores}
        self._received = dict.fromkeys(self._items, 0)
        self._jobs = {}
        self._loads = {}
        self._busy = {}
        self._manifests = {}
        self._commands = {}
        self._audit = []
        self._clock = 0

    def _before_command(self, at_s):
        """Extension hook for scheduled physical operations."""

    @staticmethod
    def _index(objects, kind, key):
        result = {}
        for obj in objects:
            if not isinstance(obj, kind) or getattr(obj, key) in result:
                raise ValueError("invalid or duplicate configuration")
            result[getattr(obj, key)] = obj
        return result

    def snapshot(self):
        """Detached state for diagnostics; callers cannot mutate the ledger."""
        return deepcopy(
            {
                "stock": self._stock,
                "jobs": self._jobs,
                "loads": self._loads,
                "busy": self._busy,
                "manifests": self._manifests,
                "audit": self._audit,
                "clock": self._clock,
            }
        )

    def _quantities(self, quantities):
        if not isinstance(quantities, dict) or not quantities:
            raise ValueError("nonempty quantity mapping required")
        for item, quantity in quantities.items():
            if item not in self._items:
                raise ValueError("unknown item")
            natural(quantity, "quantity", True)

    def _job(self, mission_id):
        if mission_id not in self._jobs:
            raise ValueError("unknown mission")
        return self._jobs[mission_id]

    def available(self, depot_id, item_id):
        if depot_id not in self._stores or item_id not in self._items:
            raise ValueError("unknown depot/item")
        reserved = sum(
            j.reserved.get(item_id, 0)
            for j in self._jobs.values()
            if j.mission.origin_id == depot_id
        )
        return self._stock[depot_id].get(item_id, 0) - reserved

    def _capacity(self, depot_id):
        stock = self._stock[depot_id]
        store = self._stores[depot_id]
        for cold, capacity in [(False, store.ordinary_m3), (True, store.cold_m3)]:
            used = sum(
                (
                    self._items[i].m3 * q
                    for i, q in stock.items()
                    if self._items[i].cold == cold
                ),
                Decimal(0),
            )
            if used > capacity:
                raise ValueError("depot capacity exceeded")

    def _check(self):
        for depot, stock in self._stock.items():
            self._capacity(depot)
            for item, quantity in stock.items():
                if quantity < 0 or self.available(depot, item) < 0:
                    raise ValueError("stock/reservation invariant violated")
        for item in self._items:
            stored = sum(stock.get(item, 0) for stock in self._stock.values())
            loaded = sum(
                q
                for manifest in self._manifests.values()
                for (_, _, i), q in manifest.items()
                if i == item
            )
            if stored + loaded != self._received[item]:
                raise ValueError("quantity conservation violated")

    @command
    def receive(self, command_id, at_s, depot_id, quantities):
        """Commit inspected, usable stock, never a scheduled incoming supply."""
        self._quantities(quantities)
        if depot_id not in self._stores:
            raise ValueError("unknown depot")
        for item, quantity in quantities.items():
            stock = self._stock[depot_id]
            stock[item] = stock.get(item, 0) + quantity
            self._received[item] += quantity
        return dict(quantities)

    @command
    def register(self, command_id, at_s, mission, urgent=False):
        if not isinstance(mission, Mission) or type(urgent) is not bool:
            raise ValueError("invalid mission/urgency")
        if mission.simulation_id != self.simulation_id:
            raise ValueError("foreign simulation")
        if mission.mission_id in self._jobs or at_s > mission.start_s:
            raise ValueError("duplicate mission or registration after start")
        for depot in (mission.origin_id, mission.destination_id):
            if depot not in self._stores:
                raise ValueError("unknown mission depot")
            for line in mission.lines:
                if line.item_id not in self._items:
                    raise ValueError("unknown mission item")
                item = self._items[line.item_id]
                capacity = (
                    self._stores[depot].cold_m3
                    if item.cold
                    else self._stores[depot].ordinary_m3
                )
                if capacity < item.m3:
                    raise ValueError("incompatible depot")
        self._jobs[mission.mission_id] = Job(mission, urgent, len(self._jobs))
        self._manifests[mission.mission_id] = {}

    @command
    def reserve(self, command_id, at_s, mission_id):
        """Reserve up to full request; urgent jobs can take unlocked reserves."""
        job = self._job(mission_id)
        if job.status != "waiting":
            raise ValueError("only waiting missions can reserve")
        transfers = []
        for line in job.mission.lines:
            item = line.item_id
            needed = line.requested - job.reserved.get(item, 0)
            origin = job.mission.origin_id
            free = min(needed, self.available(origin, item))
            job.reserved[item] = job.reserved.get(item, 0) + free
            needed -= free
            if job.urgent and needed:
                # Deterministic choice: take from least urgent ordinary deadline first.
                donors = sorted(
                    self._jobs.items(),
                    key=lambda p: (p[1].mission.deadline_s, p[1].order),
                    reverse=True,
                )
                for donor_id, donor in donors:
                    if (
                        donor.urgent
                        or donor.status != "waiting"
                        or donor.mission.origin_id != origin
                    ):
                        continue
                    take = min(needed, donor.reserved.get(item, 0))
                    if take:
                        donor.reserved[item] -= take
                        job.reserved[item] += take
                        needed -= take
                        transfers.append((donor_id, item, take))
        return {"reserved": dict(job.reserved), "transfers": transfers}

    def ready(self, mission_id):
        job = self._job(mission_id)
        return job.status == "waiting" and all(
            job.reserved.get(line.item_id, 0)
            >= (line.minimum if job.urgent else line.requested)
            for line in job.mission.lines
        )

    @command
    def cancel(self, command_id, at_s, mission_id):
        job = self._job(mission_id)
        if job.status != "waiting":
            raise ValueError("loaded/loading cargo requires a separate recovery flow")
        released = dict(job.reserved)
        job.reserved.clear()
        job.status = "cancelled"
        return released

    @command
    def start_loading(self, command_id, at_s, mission_id, plans):
        """Validate all vehicles before locking a mission-wide loading plan.

        plans = {trip_id: (vehicle_id, {item_id: quantity})}.
        Vehicles must already be at origin. Plans cover all reserved quantities.
        """
        job = self._job(mission_id)
        if not self.ready(mission_id) or at_s < job.mission.start_s:
            raise ValueError("mission not ready or before scheduled start")
        if not isinstance(plans, dict) or not plans:
            raise ValueError("nonempty loading plan required")
        totals = {}
        proposed = {}
        used = set()
        for trip, plan in plans.items():
            identifier(trip)
            if trip in self._loads or not isinstance(plan, tuple) or len(plan) != 2:
                raise ValueError("invalid/duplicate trip")
            vehicle_id, quantities = plan
            self._quantities(quantities)
            if vehicle_id not in self._vehicles:
                raise ValueError("unknown vehicle")
            if (
                vehicle_id in self._busy
                or vehicle_id in used
                or self._positions[vehicle_id] != job.mission.origin_id
            ):
                raise ValueError("vehicle busy, duplicated or not at origin")
            vehicle = self._vehicles[vehicle_id]
            kg = Decimal(0)
            m3 = Decimal(0)
            seconds = 300
            has_cold = False
            for item_id, quantity in quantities.items():
                item = self._items[item_id]
                if (item.cold and not vehicle.cold) or (
                    vehicle.cold and not item.cold_compatible
                ):
                    raise ValueError("incompatible vehicle")
                kg += item.kg * quantity
                m3 += item.m3 * quantity
                seconds += item.handling_s * quantity
                has_cold |= item.cold
                totals[item_id] = totals.get(item_id, 0) + quantity
            if kg > vehicle.max_kg or m3 > vehicle.max_m3:
                raise ValueError("vehicle capacity exceeded")
            seconds += 300 if has_cold else 0
            # Round the total operation duration once, never each unit.
            duration = ((seconds + self.tick_s - 1) // self.tick_s) * self.tick_s
            proposed[trip] = Load(
                mission_id, vehicle_id, dict(quantities), at_s, at_s + duration
            )
            used.add(vehicle_id)
        if totals != {i: q for i, q in job.reserved.items() if q}:
            raise ValueError("plan must cover the complete mission reservation")
        self._loads.update(proposed)
        for trip, load in proposed.items():
            self._busy[load.vehicle_id] = trip
        job.status = "loading"
        return {trip: load.ready_s for trip, load in proposed.items()}

    @command
    def finish_loading(self, command_id, at_s, trip_id):
        if trip_id not in self._loads:
            raise ValueError("unknown trip")
        load = self._loads[trip_id]
        if load.status != "loading" or at_s < load.ready_s:
            raise ValueError("loading already completed or not ready")
        job = self._job(load.mission_id)
        stock = self._stock[job.mission.origin_id]
        manifest = self._manifests[load.mission_id]
        for item, quantity in load.quantities.items():
            stock[item] -= quantity
            job.reserved[item] -= quantity
            # Length prefix makes the pair encoding unambiguous for arbitrary IDs.
            batch = f"{len(trip_id)}:{trip_id}{item}"
            manifest[(trip_id, batch, item)] = quantity
        load.status = "loaded"
        return {key: q for key, q in manifest.items() if key[0] == trip_id}

    @command
    def depart(self, command_id, at_s, mission_id):
        job = self._job(mission_id)
        trips = [load for load in self._loads.values() if load.mission_id == mission_id]
        if (
            job.status != "loading"
            or not trips
            or any(load.status != "loaded" for load in trips)
        ):
            raise ValueError("all mission vehicles must finish loading first")
        for load in trips:
            load.status = "en_route"
        job.status = "en_route"
        return deepcopy(self._manifests[mission_id])

    def manifest(self, mission_id):
        self._job(mission_id)
        return deepcopy(self._manifests[mission_id])

    def evaluate(self, mission_id, deliveries: list[Delivery], cutoff_s):
        """Export boundary: evaluate external inspected-delivery histories.

        Does not mutate warehouse stock or free vehicles; unloading is next block.
        """
        job = self._job(mission_id)
        if job.status != "en_route":
            raise ValueError("mission has not departed")
        departed = next(
            a["at_s"]
            for a in self._audit
            if a["operation"] == "depart" and a["arguments"] == (mission_id,)
        )
        natural(cutoff_s, "cutoff_s")
        if cutoff_s < departed or any(
            e.occurred_s < departed for e in deliveries if e.observed_s <= cutoff_s
        ):
            raise ValueError("delivery/cutoff precedes departure")
        return replay(job.mission, self.manifest(mission_id), deliveries, cutoff_s)
