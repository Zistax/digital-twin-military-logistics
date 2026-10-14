"""Conservative creation-time estimates from currently observable inputs only."""

from dataclasses import dataclass
from decimal import ROUND_CEILING

from .core import Mission
from .roads import NoRoute


@dataclass(frozen=True)
class InitialEstimate:
    observed_s: int
    duration_s: int | None
    reason: str | None
    method: str = "observable-free-fleet-v1"


def estimate_request(warehouse, request):
    """Estimate a full requested load; do not guess release times of busy vehicles.

    Uses public operational facts: usable stock, expected supplier promises,
    current vehicle availability, planned handling completion, calendars and
    current road conditions. No sampling or simulation-forward is performed.
    """
    w, now = warehouse, request.start_s
    if w._clock != now:
        raise ValueError("advance exactly to request creation before estimating")
    origin, destination = request.origin_id, request.destination_id
    if origin not in w._stores or destination not in w._stores:
        raise ValueError("unknown request depot")
    quantities = {line.item_id: line.requested for line in request.lines}
    w._validate_depot_items(origin, quantities)
    w._validate_depot_items(destination, quantities)

    def unavailable(reason):
        return InitialEstimate(now, None, reason)

    def opening(depot, at):
        calendar = w._operations[depot].calendar
        while not calendar.is_open(w._epoch, at):
            at = calendar.next_change(w._epoch, at)
        return at

    def handling(cargo):
        seconds = 300 + sum(w._items[i].handling_s * q for i, q in cargo.items())
        if any(w._items[i].cold for i in cargo):
            seconds += 300
        return ((seconds + w.tick_s - 1) // w.tick_s) * w.tick_s

    def slots(depot):
        times = [
            max(now, op["end_s"]) for op in w._active.values() if op["depot"] == depot
        ]
        times += [now] * (w._operations[depot].berths - len(times))
        for trip, queued in sorted(w._queue.items()):
            if queued["depot"] == depot:
                duration = queued.get("duration", handling(w._loads[trip].quantities))
                index = min(range(len(times)), key=times.__getitem__)
                times[index] = opening(depot, times[index]) + duration
        return times

    ready = now
    supplies = w.observed_supplies()
    for item, quantity in quantities.items():
        missing = max(0, quantity - w.available(origin, item))
        if not missing:
            continue
        for supply in sorted(supplies.values(), key=lambda s: s["expected_s"]):
            if supply["depot"] != origin or supply["status"] != "expected":
                continue
            promised = supply["ordered"].get(item, 0)
            if promised and supply["expected_s"] > now:
                missing -= promised
                ready = max(
                    ready,
                    opening(origin, supply["expected_s"]) + handling(supply["ordered"]),
                )
            if missing <= 0:
                break
        if missing > 0:
            return unavailable("stock_without_usable_arrival_promise")
    candidates = []
    for v, vehicle in sorted(w._vehicles.items()):
        if v in w._busy or v in w._broken or w._positions[v] is None:
            continue
        try:
            _, travel = w._network.route(w._positions[v], origin, w._occupancy())
        except NoRoute:
            continue
        candidates.append((travel, v))
    candidates.sort()
    cargo = {v: {} for _, v in candidates}
    capacity = {
        v: [w._vehicles[v].max_kg, w._vehicles[v].max_m3] for _, v in candidates
    }

    def compatible(i, v):
        item, vehicle = w._items[i], w._vehicles[v]
        return (not item.cold or vehicle.cold) and (
            not vehicle.cold or item.cold_compatible
        )

    for i in sorted(
        quantities,
        key=lambda i: (
            sum(compatible(i, v) for _, v in candidates),
            -w._items[i].m3,
            -w._items[i].kg,
            i,
        ),
    ):
        remaining = quantities[i]
        for _, v in candidates:
            if not compatible(i, v):
                continue
            item = w._items[i]
            take = min(
                remaining,
                int(capacity[v][0] // item.kg),
                int(capacity[v][1] // item.m3),
            )
            if take:
                cargo[v][i] = take
                capacity[v][0] -= take * item.kg
                capacity[v][1] -= take * item.m3
                remaining -= take
        if remaining:
            return unavailable("insufficient_free_compatible_fleet")
    for cold in (False, True):
        needed = sum(
            w._items[i].m3 * q
            for i, q in quantities.items()
            if w._items[i].cold == cold
        )
        if needed > w._space(destination, cold, False):
            return unavailable("destination_space")
    try:
        _, loaded_travel = w._network.route(origin, destination, w._occupancy())
    except NoRoute:
        return unavailable("no_route")
    origin_slots, destination_slots = slots(origin), slots(destination)
    loaded = []
    for travel, v in candidates:
        if not cargo[v]:
            continue
        index = min(range(len(origin_slots)), key=origin_slots.__getitem__)
        end = opening(origin, max(ready, now + travel, origin_slots[index])) + handling(
            cargo[v]
        )
        origin_slots[index] = end
        loaded.append((end, v))
    departure = max(end for end, _ in loaded)
    for _, v in loaded:
        index = min(range(len(destination_slots)), key=destination_slots.__getitem__)
        destination_slots[index] = opening(
            destination, max(departure + loaded_travel, destination_slots[index])
        ) + handling(cargo[v])
    return InitialEstimate(now, max(destination_slots) - now, None)


def mission_from_estimate(simulation_id, request, estimate):
    if estimate.observed_s != request.start_s or estimate.duration_s is None:
        raise ValueError("finite estimate at request creation required")
    duration = int(
        (request.deadline_margin * estimate.duration_s).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    return Mission(
        simulation_id,
        request.request_id,
        request.origin_id,
        request.destination_id,
        request.start_s,
        request.start_s + max(1, duration),
        request.lines,
    )
