"""Automatic fleet allocation and event-driven road movement."""

from copy import deepcopy

from .operations import OperationsWarehouse
from .roads import Network, NoRoute
from .warehouse import command


class TransportWarehouse(OperationsWarehouse):
    def __init__(self, *args, network, **kwargs):
        super().__init__(*args, **kwargs)
        if not isinstance(network, Network) or any(
            d not in network.nodes for d in self._stores
        ):
            raise ValueError("network must include every depot")
        self._network = deepcopy(network)
        self._road = {}
        self._scheduled = set()
        self._pending = {}
        self._allocation_wait = {}
        self._transport_log = []
        self._trip_sequence = 0

    def snapshot(self):
        result = super().snapshot()
        result.update(
            deepcopy(
                {
                    "road_movements": self._road,
                    "pending_assignments": self._pending,
                    "allocation_wait": self._allocation_wait,
                    "transport_log": self._transport_log,
                }
            )
        )
        return result

    def _occupancy(self):
        counts = {}
        for movement in self._road.values():
            if movement["end_s"] is not None:
                key = self._network.key(*movement["path"][:2])
                counts[key] = counts.get(key, 0) + 1
        return counts

    @command
    def schedule(self, command_id, at_s, mission_id):
        job = self._job(mission_id)
        if job.status != "waiting" or any(
            entry.mission_id == mission_id for entry in self._loads.values()
        ):
            raise ValueError("schedule before creating a loading plan")
        self._scheduled.add(mission_id)

    @command
    def road_condition(self, command_id, at_s, first, second, **condition):
        self._network.set_condition(first, second, **condition)
        self._transport_log.append(
            {
                "kind": "condition",
                "at_s": at_s,
                "edge": self._network.key(first, second),
                "condition": dict(condition),
            }
        )

    def _pack(self, mission_id):
        job = self._job(mission_id)
        origin = job.mission.origin_id
        candidates = []
        for vehicle_id, vehicle in self._vehicles.items():
            if vehicle_id in self._busy or self._positions[vehicle_id] is None:
                continue
            try:
                path, eta = self._network.route(
                    self._positions[vehicle_id], origin, self._occupancy()
                )
            except NoRoute:
                continue
            candidates.append((eta, vehicle_id, path))
        candidates.sort()
        remaining = {i: q for i, q in job.reserved.items() if q}
        capacities = {
            v: [self._vehicles[v].max_kg, self._vehicles[v].max_m3]
            for _, v, _ in candidates
        }
        quantities = {v: {} for _, v, _ in candidates}

        def compatible(item_id, vehicle_id):
            item, vehicle = self._items[item_id], self._vehicles[vehicle_id]
            return (not item.cold or vehicle.cold) and (
                not vehicle.cold or item.cold_compatible
            )

            # Most constrained cargo first, then large units. Vehicles ranked by ETA.

        order = sorted(
            remaining,
            key=lambda i: (
                sum(compatible(i, v) for _, v, _ in candidates),
                -self._items[i].m3,
                -self._items[i].kg,
                i,
            ),
        )
        for item_id in order:
            item = self._items[item_id]
            for _, vehicle_id, path in candidates:
                if not compatible(item_id, vehicle_id):
                    continue
                kg, m3 = capacities[vehicle_id]
                count = min(remaining[item_id], int(kg // item.kg), int(m3 // item.m3))
                if count:
                    quantities[vehicle_id][item_id] = count
                    capacities[vehicle_id] = [
                        kg - item.kg * count,
                        m3 - item.m3 * count,
                    ]
                    remaining[item_id] -= count
            if remaining[item_id]:
                return None
        return [(v, quantities[v], path) for _, v, path in candidates if quantities[v]]

    def _make_movement(self, vehicle_id, path, mission_id, trip, at_s):
        self._road[vehicle_id] = {
            "path": tuple(path),
            "target": path[-1],
            "node": path[0],
            "mission_id": mission_id,
            "trip_id": trip,
            "end_s": None,
            "started_s": at_s,
            "blocked": False,
        }
        self._enter(vehicle_id, at_s)

    def _enter(self, vehicle_id, at_s):
        movement = self._road[vehicle_id]
        if movement["end_s"] is not None:
            return
        old_path = movement["path"]
        occupancy = self._occupancy()
        try:
            path, eta = self._network.route(
                movement["node"], movement["target"], occupancy
            )
        except NoRoute:
            if not movement["blocked"]:
                self._transport_log.append(
                    {
                        "kind": "route_blocked",
                        "at_s": at_s,
                        "vehicle_id": vehicle_id,
                        "node": movement["node"],
                    }
                )
            movement["blocked"] = True
            self._positions[vehicle_id] = movement["node"]
            return
        try:
            old_eta = self._network.path_seconds(old_path, occupancy)
            saving = old_eta - eta
            change = saving >= 300 and saving >= old_eta * 0.1
            reason = "time_saving"
        except (NoRoute, KeyError):
            change, reason = True, "road_closed"
        if change:
            movement["path"] = path
            self._transport_log.append(
                {
                    "kind": "reroute",
                    "at_s": at_s,
                    "vehicle_id": vehicle_id,
                    "reason": reason,
                    "old_path": old_path,
                    "new_path": path,
                    "new_eta_s": eta,
                }
            )
        movement["blocked"] = False
        path = movement["path"]
        duration = self._network.seconds(path[0], path[1], occupancy)
        movement["started_s"] = at_s
        movement["end_s"] = at_s + duration
        self._positions[vehicle_id] = None
        self._transport_log.append(
            {
                "kind": "edge_enter",
                "at_s": at_s,
                "vehicle_id": vehicle_id,
                "edge": path[:2],
                "end_s": at_s + duration,
                "empty": movement["trip_id"] is None,
            }
        )

    def _allocate(self, at_s):
        # Empty trips finish before any fresh allocation at this timestamp.
        for mission_id, plan in list(self._pending.items()):
            origin = self._job(mission_id).mission.origin_id
            if all(
                v not in self._road and self._positions[v] == origin for v, _, _ in plan
            ):
                for v, _, _ in plan:
                    self._busy.pop(v, None)
                del self._pending[mission_id]
        jobs = sorted(
            self._scheduled,
            key=lambda mid: (
                not self._job(mid).urgent,
                self._job(mid).mission.deadline_s,
                self._job(mid).order,
                mid,
            ),
        )
        for mission_id in jobs:
            job = self._job(mission_id)
            if job.status not in ("waiting", "loading") or job.mission.start_s > at_s:
                continue
            previous = dict(job.reserved)
            reserved = OperationsWarehouse.reserve.__wrapped__(
                self, "auto", at_s, mission_id
            )
            if previous != job.reserved or reserved["transfers"]:
                self._transport_log.append(
                    {
                        "kind": "reservation",
                        "at_s": at_s,
                        "mission_id": mission_id,
                        **reserved,
                    }
                )
            if mission_id in self._pending:
                self._allocation_wait[mission_id] = "empty_travel"
                continue
            if any(entry.mission_id == mission_id for entry in self._loads.values()):
                continue
            if not self.ready(mission_id):
                self._allocation_wait[mission_id] = "stock"
                continue
            plan = self._pack(mission_id)
            if plan is None:
                self._allocation_wait[mission_id] = "no_feasible_greedy_plan"
                continue
            origin = job.mission.origin_id
            if any(self._positions[v] != origin for v, _, _ in plan):
                self._pending[mission_id] = plan
                for vehicle_id, quantities, path in plan:
                    self._busy[vehicle_id] = ("empty", mission_id, vehicle_id)
                    if self._positions[vehicle_id] != origin:
                        self._make_movement(vehicle_id, path, mission_id, None, at_s)
                self._allocation_wait[mission_id] = "empty_travel"
            else:
                self._trip_sequence += 1
                plans = {
                    f"auto-{self ._trip_sequence }-{n }": (v, q)
                    for n, (v, q, _) in enumerate(plan)
                }
                if any(t in self._loads for t in plans):
                    raise ValueError("automatic trip ID collision")
                OperationsWarehouse.queue_loading.__wrapped__(
                    self, "auto", at_s, mission_id, plans
                )
                self._allocation_wait.pop(mission_id, None)
                self._transport_log.append(
                    {
                        "kind": "assignment",
                        "at_s": at_s,
                        "mission_id": mission_id,
                        "plans": deepcopy(plans),
                    }
                )

    def _begin_loaded(self, mission_id, at_s):
        job = self._job(mission_id)
        loads = [
            (t, entry)
            for t, entry in self._loads.items()
            if entry.mission_id == mission_id
        ]
        # Compute every route before mutating the group departure.
        routes = {
            t: self._network.route(
                job.mission.origin_id, job.mission.destination_id, self._occupancy()
            )[0]
            for t, entry in loads
        }
        result = OperationsWarehouse.depart.__wrapped__(self, "auto", at_s, mission_id)
        for trip, load in sorted(loads):
            self._make_movement(load.vehicle_id, routes[trip], mission_id, trip, at_s)
        self._transport_log.append(
            {"kind": "departure", "at_s": at_s, "mission_id": mission_id}
        )
        return result

    @command
    def depart(self, command_id, at_s, mission_id):
        return self._begin_loaded(mission_id, at_s)

    def arrive(self, *args, **kwargs):
        raise ValueError("arrivals are generated by road movement")

    @command
    def cancel(self, command_id, at_s, mission_id):
        result = OperationsWarehouse.cancel.__wrapped__(
            self, command_id, at_s, mission_id
        )
        self._scheduled.discard(mission_id)
        for vehicle_id, _, _ in self._pending.pop(mission_id, []):
            if vehicle_id not in self._road:
                self._busy.pop(vehicle_id, None)
        self._allocation_wait.pop(mission_id, None)
        return result

    def _dispatch(self, at_s):
        for vehicle_id in sorted(self._road):
            self._enter(vehicle_id, at_s)
        self._allocate(at_s)
        super()._dispatch(at_s)
        for mission_id in sorted(self._scheduled):
            job = self._job(mission_id)
            loads = [
                entry
                for entry in self._loads.values()
                if entry.mission_id == mission_id
            ]
            if (
                job.status == "loading"
                and loads
                and all(entry.status == "loaded" for entry in loads)
            ):
                try:
                    self._begin_loaded(mission_id, at_s)
                    self._allocation_wait.pop(mission_id, None)
                except NoRoute:
                    self._allocation_wait[mission_id] = "road_closed"

    def _finish(self, at_s):
        super()._finish(at_s)
        for vehicle_id, movement in sorted(list(self._road.items())):
            if movement["end_s"] != at_s:
                continue
            movement["path"] = movement["path"][1:]
            movement["node"] = movement["path"][0]
            movement["end_s"] = None
            self._positions[vehicle_id] = movement["node"]
            self._transport_log.append(
                {
                    "kind": "edge_exit",
                    "at_s": at_s,
                    "vehicle_id": vehicle_id,
                    "node": movement["node"],
                }
            )
            if movement["node"] == movement["target"]:
                del self._road[vehicle_id]
                if movement["trip_id"] is not None:
                    OperationsWarehouse.arrive.__wrapped__(
                        self, "road", at_s, movement["trip_id"]
                    )
                elif self._job(movement["mission_id"]).status == "cancelled":
                    self._busy.pop(vehicle_id, None)

    def _extra_event_times(self, cursor):
        times = [m["end_s"] for m in self._road.values() if m["end_s"] is not None]
        times += [
            self._job(mid).mission.start_s
            for mid in self._scheduled
            if self._job(mid).mission.start_s > cursor
        ]
        return times
