"""Calendar-aware shared berths and operational unloading.

Use queue_loading, advance, depart, arrive, advance; never legacy manual
start/finish_loading. Travel arrival is supplied externally in this block.
"""

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal

from .calendars import Calendar
from .core import Delivery, natural, replay
from .warehouse import Warehouse, command, measure


@dataclass(frozen=True)
class DepotOperations:
    calendar: Calendar
    berths: int = 1
    quarantine_m3: Decimal = Decimal(0)
    quarantine_cold_m3: Decimal = Decimal(0)

    def __post_init__(self):
        if not isinstance(self.calendar, Calendar):
            raise ValueError("calendar required")
        natural(self.berths, "berths", True)
        measure(self.quarantine_m3, "quarantine_m3")
        measure(self.quarantine_cold_m3, "quarantine_cold_m3")


class OperationsWarehouse(Warehouse):
    def __init__(self, *args, epoch, operations, **kwargs):
        super().__init__(*args, **kwargs)
        if not isinstance(epoch, datetime) or epoch.tzinfo is None:
            raise ValueError("timezone-aware epoch required")
        if epoch.microsecond:
            raise ValueError("epoch must have whole-second precision")
        if set(operations) != set(self._stores) or any(
            not isinstance(v, DepotOperations) for v in operations.values()
        ):
            raise ValueError("operations required for every depot")
        self._epoch = epoch.astimezone(timezone.utc)
        self._operations = dict(operations)
        self._queue = {}
        self._active = {}
        self._events = []
        self._departed = {}
        self._onboard = {}
        self._bad_onboard = {}
        self._quarantine = {d: {} for d in self._stores}
        self._wait = {}
        self._history = []
        self._engine_s = 0
        self._removed = dict.fromkeys(self._items, 0)
        self._quarantine_entries = []
        self._loaded_at = {}
        self._completed_at = {}

    def snapshot(self):
        result = super().snapshot()
        result.update(
            deepcopy(
                {
                    "queue": self._queue,
                    "active": self._active,
                    "deliveries": self._events,
                    "onboard": self._onboard,
                    "quarantine": self._quarantine,
                    "positions": self._positions,
                    "wait_seconds": self._wait,
                    "operations": self._history,
                }
            )
        )
        return result

    def _before_command(self, at_s):
        # Finish events at the target before inputs, but batch new admissions until
        # explicit advance (or until time next moves beyond this instant).
        self._advance(at_s, dispatch_target=False)

    def _check(self):
        if not hasattr(self, "_onboard"):
            return super()._check()
        for depot, stock in self._stock.items():
            self._capacity(depot)
            for item, quantity in stock.items():
                if quantity < 0 or self.available(depot, item) < 0:
                    raise ValueError("stock/reservation invariant violated")
            for cold in (False, True):
                if self._space(depot, cold, False) < 0:
                    raise ValueError("incoming space overbooked")
                if self._space(depot, cold, True) < 0:
                    raise ValueError("quarantine capacity exceeded")
            active = sum(op["depot"] == depot for op in self._active.values())
            if active > self._operations[depot].berths:
                raise ValueError("berth capacity exceeded")
        for item in self._items:
            total = sum(s.get(item, 0) for s in self._stock.values())
            total += sum(s.get(item, 0) for s in self._quarantine.values())
            total += sum(q for (_, _, i), q in self._onboard.items() if i == item)
            if total + self._removed[item] != self._received[item]:
                raise ValueError("physical quantity conservation violated")
        if len(set(self._busy.values())) != len(self._busy):
            raise ValueError("vehicle assignment invariant violated")

    def _protected(self, mission_id, item):
        return sum(
            self._loads[t].quantities.get(item, 0)
            for t, op in self._active.items()
            if op["kind"] == "load" and self._loads[t].mission_id == mission_id
        )

    def ready(self, mission_id):
        job = self._job(mission_id)
        loaded = {}
        for (_, _, item), q in self._manifests[mission_id].items():
            loaded[item] = loaded.get(item, 0) + q
        return job.status in ("waiting", "loading") and all(
            job.reserved.get(line.item_id, 0) + loaded.get(line.item_id, 0)
            >= (line.minimum if job.urgent else line.requested)
            for line in job.mission.lines
        )

    @command
    def reserve(self, command_id, at_s, mission_id):
        job = self._job(mission_id)
        if job.status not in ("waiting", "loading"):
            raise ValueError("mission cannot reserve")
        transfers = []
        for line in job.mission.lines:
            item = line.item_id
            loaded = sum(
                q for (_, _, i), q in self._manifests[mission_id].items() if i == item
            )
            planned = [
                load for load in self._loads.values() if load.mission_id == mission_id
            ]
            target = (
                sum(load.quantities.get(item, 0) for load in planned)
                if planned
                else line.requested
            )
            needed = target - loaded - job.reserved.get(item, 0)
            origin = job.mission.origin_id
            free = min(needed, self.available(origin, item))
            job.reserved[item] = job.reserved.get(item, 0) + free
            needed -= free
            if not job.urgent:
                continue
            donors = sorted(
                self._jobs.items(),
                key=lambda p: (p[1].mission.deadline_s, p[1].order),
                reverse=True,
            )
            for donor_id, donor in donors:
                if (
                    donor.urgent
                    or donor.status not in ("waiting", "loading")
                    or donor.mission.origin_id != origin
                ):
                    continue
                unlocked = donor.reserved.get(item, 0) - self._protected(donor_id, item)
                take = min(needed, max(0, unlocked))
                if take:
                    donor.reserved[item] -= take
                    job.reserved[item] += take
                    needed -= take
                    transfers.append((donor_id, item, take))
        return {"reserved": dict(job.reserved), "transfers": transfers}

    @command
    def queue_loading(self, command_id, at_s, mission_id, plans):
        job = self._job(mission_id)
        if any(load.mission_id == mission_id for load in self._loads.values()):
            raise ValueError("mission already has a loading plan")
            # Reuse the complete plan validator; convert starts to queued operations.
        result = Warehouse.start_loading.__wrapped__(
            self, command_id, at_s, mission_id, plans
        )
        job.status = "waiting"
        for trip in result:
            load = self._loads[trip]
            duration = load.ready_s - load.started_s
            load.status = "queued"
            self._queue[trip] = {
                "kind": "load",
                "depot": job.mission.origin_id,
                "duration": duration,
            }
            self._wait[trip] = dict.fromkeys(("opening", "stock", "space", "berth"), 0)
        return list(result)

    def start_loading(self, *args, **kwargs):
        raise ValueError("use queue_loading and advance in operational mode")

    def finish_loading(self, *args, **kwargs):
        raise ValueError("loading completion is automatic in operational mode")

    @command
    def cancel(self, command_id, at_s, mission_id):
        job = self._job(mission_id)
        if job.status != "waiting":
            raise ValueError("loading/loaded cargo requires recovery flow")
        for trip, load in list(self._loads.items()):
            if load.mission_id == mission_id:
                if load.status != "queued":
                    raise ValueError("cannot cancel active cargo")
                del self._queue[trip]
                del self._busy[load.vehicle_id]
                del self._loads[trip]
        released = dict(job.reserved)
        job.reserved.clear()
        job.status = "cancelled"
        return released

    @command
    def depart(self, command_id, at_s, mission_id):
        result = Warehouse.depart.__wrapped__(self, command_id, at_s, mission_id)
        self._departed[mission_id] = at_s
        for load in self._loads.values():
            if load.mission_id == mission_id:
                self._positions[load.vehicle_id] = None
        return result

    @command
    def arrive(self, command_id, at_s, trip_id, damaged=None):
        if trip_id not in self._loads or self._loads[trip_id].status != "en_route":
            raise ValueError("trip must be en route")
        load = self._loads[trip_id]
        if at_s <= self._departed[load.mission_id]:
            raise ValueError("arrival must follow departure")
        damaged = {} if damaged is None else damaged
        if not isinstance(damaged, dict):
            raise ValueError("damage mapping required")
        for item, q in damaged.items():
            natural(q, "damaged")
            if item not in load.quantities or q > load.quantities[item]:
                raise ValueError("invalid damaged quantity")
        for key in self._onboard:
            if key[0] == trip_id:
                self._bad_onboard[key] = damaged.get(key[2], 0)
        depot = self._job(load.mission_id).mission.destination_id
        self._positions[load.vehicle_id] = depot
        load.status = "unload_wait"
        self._queue[trip_id] = {"kind": "unload", "depot": depot}

    def _space(self, depot, cold, quarantine):
        config = self._operations[depot] if quarantine else self._stores[depot]
        if quarantine:
            capacity = config.quarantine_cold_m3 if cold else config.quarantine_m3
            stock = self._quarantine[depot]
        else:
            capacity = config.cold_m3 if cold else config.ordinary_m3
            stock = self._stock[depot]
        used = sum(
            (
                self._items[i].m3 * q
                for i, q in stock.items()
                if self._items[i].cold == cold
            ),
            Decimal(0),
        )
        for op in self._active.values():
            if op["kind"] == "unload" and op["depot"] == depot:
                for (_, _, item), (good, bad) in op["selection"].items():
                    if self._items[item].cold == cold:
                        used += self._items[item].m3 * (bad if quarantine else good)
        return capacity - used

    def _selection(self, trip):
        depot = self._queue[trip]["depot"]
        free = {
            (cold, bad): self._space(depot, cold, bad)
            for cold in (False, True)
            for bad in (False, True)
        }
        selected = {}
        for key, quantity in sorted(self._onboard.items()):
            if key[0] != trip or quantity == 0:
                continue
            item = self._items[key[2]]
            bad = self._bad_onboard.get(key, 0)
            good = min(quantity - bad, int(free[item.cold, False] // item.m3))
            bad = min(bad, int(free[item.cold, True] // item.m3))
            if good + bad:
                selected[key] = (good, bad)
                free[item.cold, False] -= good * item.m3
                free[item.cold, True] -= bad * item.m3
        return selected

    def _reason(self, trip, at_s):
        request = self._queue[trip]
        depot = request["depot"]
        if not self._operations[depot].calendar.is_open(self._epoch, at_s):
            return "opening"
        load = self._loads[trip]
        if request["kind"] == "load":
            job = self._job(load.mission_id)
            if not self.ready(load.mission_id) or any(
                job.reserved.get(i, 0) - self._protected(load.mission_id, i) < q
                for i, q in load.quantities.items()
            ):
                return "stock"
        elif not self._selection(trip):
            return "space"
        return "berth"

    def _dispatch(self, at_s):
        def priority(trip):
            job = self._job(self._loads[trip].mission_id)
            return (not job.urgent, job.mission.deadline_s, job.order, trip)

        for trip in sorted(list(self._queue), key=priority):
            request = self._queue[trip]
            depot = request["depot"]
            if (
                self._reason(trip, at_s) != "berth"
                or sum(op["depot"] == depot for op in self._active.values())
                >= self._operations[depot].berths
            ):
                continue
            op = dict(request)
            load = self._loads[trip]
            if op["kind"] == "load":
                duration = op["duration"]
                load.status = "loading"
                self._job(load.mission_id).status = "loading"
            else:
                selection = self._selection(trip)
                op["selection"] = selection
                seconds = 300 + sum(
                    self._items[k[2]].handling_s * sum(q) for k, q in selection.items()
                )
                if any(self._items[k[2]].cold for k in selection):
                    seconds += 300
                duration = ((seconds + self.tick_s - 1) // self.tick_s) * self.tick_s
                load.status = "unloading"
            op.update(start_s=at_s, end_s=at_s + duration)
            load.started_s, load.ready_s = at_s, at_s + duration
            del self._queue[trip]
            self._active[trip] = op

    def _finish(self, at_s):
        for entry in list(self._quarantine_entries):
            depot, item, quantity, due = entry
            calendar = self._operations[depot].calendar
            if due <= at_s and calendar.is_open(self._epoch, at_s):
                self._quarantine[depot][item] -= quantity
                self._removed[item] += quantity
                self._quarantine_entries.remove(entry)
                self._history.append(
                    {
                        "kind": "quarantine_removal",
                        "depot": depot,
                        "item": item,
                        "quantity": quantity,
                        "at_s": at_s,
                    }
                )
        for trip, op in sorted(
            list(self._active.items()), key=lambda pair: str(pair[0])
        ):
            if op["end_s"] != at_s:
                continue
            del self._active[trip]  # release reserved space before crediting stock
            load = self._loads[trip]
            job = self._job(load.mission_id)
            if op["kind"] == "load":
                manifest = Warehouse.finish_loading.__wrapped__(
                    self, "internal", at_s, trip
                )
                self._onboard.update(manifest)
                self._loaded_at.update({key: at_s for key in manifest})
            else:
                for key, (good, bad) in op["selection"].items():
                    item = key[2]
                    self._onboard[key] -= good + bad
                    self._bad_onboard[key] -= bad
                    stock = self._stock[op["depot"]]
                    stock[item] = stock.get(item, 0) + good
                    stock = self._quarantine[op["depot"]]
                    stock[item] = stock.get(item, 0) + bad
                    if bad:
                        self._quarantine_entries.append(
                            (op["depot"], item, bad, at_s + 86400)
                        )
                    event_id = f"unload:{len (self ._events )}"
                    self._events.append(
                        Delivery(
                            event_id,
                            self.simulation_id,
                            load.mission_id,
                            trip,
                            key[1],
                            item,
                            at_s,
                            at_s,
                            good,
                            bad,
                        )
                    )
                if any(q for key, q in self._onboard.items() if key[0] == trip):
                    load.status = "unload_wait"
                    self._queue[trip] = {"kind": "unload", "depot": op["depot"]}
                else:
                    load.status = "completed"
                    self._completed_at[trip] = at_s
                    del self._busy[load.vehicle_id]
                    if all(
                        entry.status == "completed"
                        for entry in self._loads.values()
                        if entry.mission_id == load.mission_id
                    ):
                        job.status = "logistics_complete"
            calendar = self._operations[op["depot"]].calendar
            self._history.append(
                {
                    "trip_id": trip,
                    **op,
                    "overtime_s": calendar.closed_seconds(
                        self._epoch, op["start_s"], at_s
                    ),
                }
            )

    def _on_interval(self, start_s, end_s):
        """Continuous processes between scheduled events."""

    def _extra_event_times(self, cursor):
        return []

    def _advance(self, target, dispatch_target=True):
        cursor = self._engine_s
        while True:
            self._finish(cursor)
            if cursor < target or dispatch_target:
                self._dispatch(cursor)
            self._check()
            if hasattr(self, "_journal"):
                self._journal.capture(self, cursor)
            if cursor == target:
                break
            candidates = [target] + [op["end_s"] for op in self._active.values()]
            candidates.extend(self._extra_event_times(cursor))
            for depot, item, quantity, due in self._quarantine_entries:
                if due > cursor:
                    candidates.append(due)
                else:
                    candidates.append(
                        self._operations[depot].calendar.next_change(
                            self._epoch, cursor
                        )
                    )
            for trip, request in self._queue.items():
                calendar = self._operations[request["depot"]].calendar
                candidates.append(calendar.next_change(self._epoch, cursor))
            stop = min(t for t in candidates if t > cursor)
            for trip in self._queue:
                self._wait[trip][self._reason(trip, cursor)] += stop - cursor
            self._on_interval(cursor, stop)
            cursor = stop
            self._engine_s = cursor
        self._engine_s = target

    @command
    def advance(self, command_id, at_s):
        self._advance(at_s)
        return {trip: op["end_s"] for trip, op in self._active.items()}

    def outcome(self, mission_id, cutoff_s):
        natural(cutoff_s, "cutoff_s")
        if cutoff_s > self._clock:
            raise ValueError("advance before querying future state")
        job = self._job(mission_id)
        events = [e for e in self._events if e.mission_id == mission_id]
        manifest = self._manifest_at(mission_id, cutoff_s)
        result = replay(job.mission, manifest, events, cutoff_s)
        trips = [t for t, load in self._loads.items() if load.mission_id == mission_id]
        complete = bool(trips) and all(
            self._completed_at.get(t, cutoff_s + 1) <= cutoff_s for t in trips
        )
        return replace(result, logistics_complete=complete)

    def _manifest_at(self, mission_id, cutoff_s):
        return {
            key: q
            for key, q in self.manifest(mission_id).items()
            if self._loaded_at[key] <= cutoff_s
        }
