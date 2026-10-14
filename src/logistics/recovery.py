"""Approved replacements and supplementary trips, preserving mission identity."""

from dataclasses import replace
from copy import deepcopy

from .incidents import IncidentWarehouse
from .roads import NoRoute
from .warehouse import Load, command


class RecoveryWarehouse(IncidentWarehouse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rescues = {}
        self._reinforcements = {}
        self._cancelled = {}
        self._splits = []

    def snapshot(self):
        state = super().snapshot()
        state["batch_splits"] = deepcopy(self._splits)
        return state

    def _manifest_at(self, mission_id, cutoff_s):
        manifest = self.manifest(mission_id)
        for split in reversed(self._splits):
            if split["mission_id"] == mission_id and split["at_s"] > cutoff_s:
                child, parent, q = split["child"], split["parent"], split["quantity"]
                manifest.pop(child, None)
                manifest[parent] = manifest.get(parent, 0) + q
        return {
            key: q for key, q in manifest.items() if self._loaded_at[key] <= cutoff_s
        }

    def _allocate(self, at_s):
        previous = self._scheduled
        self._scheduled = previous - set(self._reinforcements) - set(self._cancelled)
        try:
            super()._allocate(at_s)
        finally:
            self._scheduled = previous

    def ready(self, mission_id):
        request_id = self._reinforcements.get(mission_id)
        if request_id is None:
            return super().ready(mission_id)
        request = self._requests[request_id]
        job = self._job(mission_id)
        loaded = {}
        for (trip, _, item), q in self._manifests[mission_id].items():
            if trip in request.get("trips", []):
                loaded[item] = loaded.get(item, 0) + q
        return all(
            job.reserved.get(i, 0) + loaded.get(i, 0) >= q
            for i, q in request["quantities"].items()
        )

    @command
    def cancel(self, command_id, at_s, mission_id, reason="operator cancellation"):
        job = self._job(mission_id)
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("cancellation reason required")
        if mission_id in self._cancelled:
            raise ValueError("mission already cancelled")
        accepted = {
            line.item_id: sum(
                e.accepted
                for e in self._events
                if e.mission_id == mission_id and e.item_id == line.item_id
            )
            for line in job.mission.lines
        }
        if all(accepted[line.item_id] >= line.minimum for line in job.mission.lines):
            raise ValueError("objective already reached")
        self._cancelled[mission_id] = at_s
        for trip, load in list(self._loads.items()):
            if load.mission_id == mission_id and load.status == "queued":
                self._queue.pop(trip, None)
                self._busy.pop(load.vehicle_id, None)
                del self._loads[trip]
        released = {}
        for item, q in job.reserved.items():
            protected = self._protected(mission_id, item)
            released[item] = q - protected
            job.reserved[item] = protected
        for vehicle_id, _, _ in self._pending.pop(mission_id, []):
            if vehicle_id not in self._road:
                self._busy.pop(vehicle_id, None)
        rid = self._reinforcements.get(mission_id)
        if rid and not self._requests[rid].get("trips"):
            self._requests[rid]["status"] = "cancelled"
            self._requests[rid]["completed_s"] = at_s
            self._approval_due.pop(rid, None)
            del self._reinforcements[mission_id]
        if not any(load.mission_id == mission_id for load in self._loads.values()):
            job.status = "cancelled"
        self._alerts.append(
            {
                "kind": "mission_cancelled",
                "at_s": at_s,
                "mission_id": mission_id,
                "reason": reason,
                "cargo_destination": job.mission.destination_id,
            }
        )
        return released

    def outcome(self, mission_id, cutoff_s):
        result = super().outcome(mission_id, cutoff_s)
        pending = any(
            r["mission_id"] == mission_id
            and r["created_s"] <= cutoff_s
            and r.get("completed_s", cutoff_s + 1) > cutoff_s
            for r in self._requests.values()
        )
        if pending:
            result = replace(result, logistics_complete=False)
        if mission_id in self._cancelled and cutoff_s >= self._cancelled[mission_id]:
            return replace(result, status="cancelled", late=None, delay_minutes=None)
        return result

    def _replacement(self, request_id, request, at_s):
        old = request["vehicle_id"]
        failure = self._broken[old]
        movement = self._road[old]
        trip = request["trip_id"]
        quantities = {
            key[2]: q for key, q in self._onboard.items() if key[0] == trip and q
        }
        a, b = movement["path"][:2]
        candidates = []
        partial_candidates = []
        try:
            edge_seconds = self._network.seconds(a, b, self._occupancy())
        except NoRoute:
            request["waiting_reason"] = "rescue_road_closed"
            return
        for vehicle_id, vehicle in sorted(self._vehicles.items()):
            if vehicle_id in self._busy or vehicle_id in self._broken:
                continue
            cargo = {}
            free_kg, free_m3 = vehicle.max_kg, vehicle.max_m3
            for i, q in sorted(
                quantities.items(), key=lambda p: (not self._items[p[0]].cold, p[0])
            ):
                item = self._items[i]
                if (item.cold and not vehicle.cold) or (
                    vehicle.cold and not item.cold_compatible
                ):
                    continue
                take = min(q, int(free_kg // item.kg), int(free_m3 // item.m3))
                if take:
                    cargo[i] = take
                    free_kg -= take * item.kg
                    free_m3 -= take * item.m3
            if not cargo:
                continue
            for endpoint, portion in (
                (a, failure["full_s"] - failure["remaining_s"]),
                (b, failure["remaining_s"]),
            ):
                try:
                    path, eta = self._network.route(
                        self._positions[vehicle_id], endpoint, self._occupancy()
                    )
                except NoRoute:
                    continue
                approach = max(
                    1,
                    (edge_seconds * portion + failure["full_s"] - 1)
                    // failure["full_s"],
                )
                target = candidates if cargo == quantities else partial_candidates
                target.append(
                    (eta + approach, vehicle_id, endpoint, path, approach, cargo)
                )
        candidates = candidates or partial_candidates
        if not candidates:
            request["waiting_reason"] = "compatible_replacement_unavailable"
            return
        _, vehicle_id, endpoint, path, approach, cargo = min(
            candidates, key=lambda c: c[:3]
        )
        self._busy[vehicle_id] = ("rescue", request_id)
        self._rescues[request_id] = {
            "vehicle_id": vehicle_id,
            "endpoint": endpoint,
            "approach_s": approach,
            "stage": "travel",
            "due_s": None,
            "quantities": cargo,
        }
        request["status"] = "in_progress"
        request["replacement_vehicle_id"] = vehicle_id
        request.pop("waiting_reason", None)
        if len(path) > 1:
            self._make_movement(vehicle_id, path, request["mission_id"], None, at_s)

    def _rescue_progress(self, at_s):
        for request_id, rescue in list(self._rescues.items()):
            request = self._requests[request_id]
            vehicle_id = rescue["vehicle_id"]
            if vehicle_id in self._broken:
                continue
            if rescue["stage"] == "travel" and vehicle_id not in self._road:
                if self._positions[vehicle_id] != rescue["endpoint"]:
                    try:
                        path = self._network.route(
                            self._positions[vehicle_id],
                            rescue["endpoint"],
                            self._occupancy(),
                        )[0]
                    except NoRoute:
                        continue
                    self._busy[vehicle_id] = ("rescue", request_id)
                    self._make_movement(
                        vehicle_id, path, request["mission_id"], None, at_s
                    )
                    continue
                rescue.update(stage="approach", due_s=at_s + rescue["approach_s"])
                self._positions[vehicle_id] = None
            elif rescue["stage"] == "approach" and rescue["due_s"] == at_s:
                trip = request["trip_id"]
                seconds = 600 + 2 * sum(
                    self._items[i].handling_s * q
                    for i, q in rescue["quantities"].items()
                )
                duration = ((seconds + self.tick_s - 1) // self.tick_s) * self.tick_s
                rescue.update(stage="transfer", due_s=at_s + duration)
                self._alerts.append(
                    {
                        "kind": "transfer_started",
                        "at_s": at_s,
                        "request_id": request_id,
                        "trip_id": trip,
                    }
                )
            elif rescue["stage"] == "transfer" and rescue["due_s"] == at_s:
                self._complete_transfer(request_id, at_s)

    def _fail(self, vehicle_id, at_s, repairable, duration):
        match = next(
            (
                (rid, r)
                for rid, r in self._rescues.items()
                if r["vehicle_id"] == vehicle_id
            ),
            None,
        )
        if match is None or match[1]["stage"] == "travel":
            super()._fail(vehicle_id, at_s, repairable, duration)
        else:
            rid, rescue = match
            if vehicle_id in self._broken or rescue["due_s"] <= at_s:
                raise ValueError("rescue must be active and not already broken")
            self._broken[vehicle_id] = {
                "repairable": repairable,
                "due_s": at_s + duration,
                "remaining_s": rescue["due_s"] - at_s,
                "origin": rescue["endpoint"],
                "cargo_managed": True,
                "rescue_id": rid,
                "failed_s": at_s,
            }
            rescue["due_s"] = None
            self._alerts.append(
                {
                    "kind": "mechanical_failure",
                    "at_s": at_s,
                    "vehicle_id": vehicle_id,
                    "repairable": repairable,
                    "rescue_stage": rescue["stage"],
                }
            )
            if self._policy.automatic:
                self._drive_left[vehicle_id] = self._clock_draw(
                    "mechanical", vehicle_id
                )
        if match is not None and not repairable:
            rid, rescue = match
            del self._rescues[rid]
            request = self._requests[rid]
            request["status"] = "approved"
            request.pop("replacement_vehicle_id", None)
            request["waiting_reason"] = "rescuer_failed"
            self._busy[vehicle_id] = ("repair", vehicle_id)
            self._alerts.append(
                {
                    "kind": "rescue_abandoned",
                    "at_s": at_s,
                    "request_id": rid,
                    "vehicle_id": vehicle_id,
                }
            )

    def _on_interval(self, start_s, end_s):
        super()._on_interval(start_s, end_s)
        if self._policy.automatic:
            for rescue in self._rescues.values():
                v = rescue["vehicle_id"]
                if rescue["stage"] == "approach" and v not in self._broken:
                    self._drive_left[v] -= end_s - start_s

    def _complete_transfer(self, request_id, at_s):
        rescue = self._rescues.pop(request_id)
        request = self._requests[request_id]
        old, new, trip = request["vehicle_id"], rescue["vehicle_id"], request["trip_id"]
        failure = self._broken[old]
        remaining_cargo = sum(q for k, q in self._onboard.items() if k[0] == trip)
        partial = sum(rescue["quantities"].values()) < remaining_cargo
        movement = deepcopy(self._road[old]) if partial else self._road.pop(old)
        if partial:
            child_trip = f"rescue:{request_id}:{len(request.get('transfers', []))}"
            if child_trip in self._loads:
                raise ValueError("rescue trip collision")
            self._loads[child_trip] = Load(
                request["mission_id"],
                new,
                dict(rescue["quantities"]),
                at_s,
                at_s,
                "en_route",
            )
            self._wait[child_trip] = dict.fromkeys(
                ("opening", "stock", "space", "berth"), 0
            )
            manifest = self._manifests[request["mission_id"]]
            for key, available in list(self._onboard.items()):
                q = rescue["quantities"].get(key[2], 0)
                if key[0] != trip or not q:
                    continue
                child = (child_trip, f"{child_trip}:{key[2]}", key[2])
                bad = min(q, self._hidden_bad.get(key, 0))
                known_bad = min(bad, self._bad_onboard.get(key, 0))
                self._onboard[key] -= q
                self._onboard[child] = q
                self._hidden_bad[key] = self._hidden_bad.get(key, 0) - bad
                self._hidden_bad[child] = bad
                self._bad_onboard[key] = self._bad_onboard.get(key, 0) - known_bad
                self._bad_onboard[child] = known_bad
                self._exposure[child] = self._exposure.get(key, 0)
                manifest[key] -= q
                if not manifest[key]:
                    del manifest[key]
                manifest[child] = q
                self._loaded_at[child] = at_s
                self._loads[trip].quantities[key[2]] -= q
                self._splits.append(
                    {
                        "mission_id": request["mission_id"],
                        "at_s": at_s,
                        "parent": key,
                        "child": child,
                        "quantity": q,
                    }
                )
            trip = child_trip
            movement["trip_id"] = trip
        for key, q in self._onboard.items():
            if key[0] == trip:
                bad = self._hidden_bad.get(key, 0)
                bad += self._damage(key, q - bad, "transfer-unload")
                bad += self._damage(key, q - bad, "transfer-load")
                self._hidden_bad[key] = bad
        self._loads[trip].vehicle_id = new
        self._busy[new] = trip
        if not partial:
            self._busy[old] = ("repair", old)
            self._positions[old] = None
            failure["cargo_managed"] = True
        # Preserve the physical fraction of the interrupted edge on the new truck.
        a, b = movement["path"][:2]
        try:
            full = self._network.seconds(a, b, self._occupancy())
        except NoRoute:
            full = failure[
                "full_s"
            ]  # already on edge, same completion rule as transport
        remaining = max(
            1,
            (full * failure["remaining_s"] + failure["full_s"] - 1)
            // failure["full_s"],
        )
        movement.update(end_s=at_s + remaining, started_s=at_s + remaining - full)
        self._road[new] = movement
        self._travel_origin[new] = failure["origin"]
        request.setdefault("transfers", []).append(
            {"trip_id": trip, "vehicle_id": new, "at_s": at_s}
        )
        request["status"] = "approved" if partial else "completed"
        if not partial:
            request["completed_s"] = at_s
        self._alerts.append(
            {
                "kind": "transfer_completed",
                "at_s": at_s,
                "request_id": request_id,
                "trip_id": trip,
                "old_vehicle": old,
                "new_vehicle": new,
            }
        )

    def _propose_reinforcements(self, at_s):
        for mission_id, job in self._jobs.items():
            if (
                job.status != "logistics_complete"
                or mission_id in self._reinforcements
                or mission_id in self._cancelled
            ):
                continue
            accepted = {}
            for event in self._events:
                if event.mission_id == mission_id:
                    accepted[event.item_id] = (
                        accepted.get(event.item_id, 0) + event.accepted
                    )
            deficit = {
                line.item_id: line.minimum - accepted.get(line.item_id, 0)
                for line in job.mission.lines
                if line.minimum > accepted.get(line.item_id, 0)
            }
            if deficit:
                req = self._request(
                    "reinforcement", mission_id, at_s, quantities=deficit
                )
                self._reinforcements[mission_id] = req
                job.status = "recovery_wait"

    def _reinforce(self, request_id, request, at_s):
        mission_id = request["mission_id"]
        job = self._job(mission_id)
        origin = job.mission.origin_id
        for item, quantity in request["quantities"].items():
            needed = quantity - job.reserved.get(item, 0)
            take = min(needed, self.available(origin, item))
            job.reserved[item] = job.reserved.get(item, 0) + take
            needed -= take
            if job.urgent and needed:
                for donor_id, donor in sorted(
                    self._jobs.items(),
                    key=lambda p: (p[1].mission.deadline_s, p[1].order),
                    reverse=True,
                ):
                    if (
                        donor_id == mission_id
                        or donor.urgent
                        or donor.status not in ("waiting", "loading")
                        or donor.mission.origin_id != origin
                    ):
                        continue
                    unlocked = max(
                        0, donor.reserved.get(item, 0) - self._protected(donor_id, item)
                    )
                    take = min(needed, unlocked)
                    if take:
                        donor.reserved[item] -= take
                        job.reserved[item] += take
                        needed -= take
                        self._alerts.append(
                            {
                                "kind": "recovery_reservation_transfer",
                                "at_s": at_s,
                                "from": donor_id,
                                "to": mission_id,
                                "item": item,
                                "quantity": take,
                            }
                        )
        if not self.ready(mission_id):
            request["waiting_reason"] = "stock"
            return
        if mission_id in self._pending:
            request["waiting_reason"] = "empty_travel"
            return
        plan = self._pack(mission_id)
        if plan is None:
            request["waiting_reason"] = "fleet"
            return
        if any(self._positions[v] != origin for v, _, _ in plan):
            self._pending[mission_id] = plan
            for v, _, path in plan:
                self._busy[v] = ("empty", mission_id, v)
                if self._positions[v] != origin:
                    self._make_movement(v, path, mission_id, None, at_s)
            request["waiting_reason"] = "empty_travel"
            return
        trips = []
        for index, (v, quantities, _) in enumerate(plan):
            trip = f"reinforcement:{request_id}:{index}"
            if trip in self._loads:
                raise ValueError("recovery trip collision")
            seconds = 300 + sum(
                self._items[i].handling_s * q for i, q in quantities.items()
            )
            if any(self._items[i].cold for i in quantities):
                seconds += 300
            duration = ((seconds + self.tick_s - 1) // self.tick_s) * self.tick_s
            self._loads[trip] = Load(
                mission_id, v, dict(quantities), at_s, at_s + duration, "queued"
            )
            self._busy[v] = trip
            self._queue[trip] = {"kind": "load", "depot": origin, "duration": duration}
            self._wait[trip] = dict.fromkeys(("opening", "stock", "space", "berth"), 0)
            trips.append(trip)
        request.update(status="in_progress", trips=trips)
        request.pop("waiting_reason", None)
        job.status = "loading"

    def inventory_position(self, depot, item, at_s=None):
        position = super().inventory_position(depot, item, at_s)
        for mid, rid in self._reinforcements.items():
            request, job = self._requests[rid], self._job(mid)
            if job.mission.origin_id != depot or request["status"] not in (
                "approved",
                "in_progress",
            ):
                continue
            if job.status in ("waiting", "loading"):
                original = sum(
                    line.requested for line in job.mission.lines if line.item_id == item
                )
                loaded = sum(
                    q for (_, _, i), q in self._manifests[mid].items() if i == item
                )
                position += max(0, original - loaded)
            recovery_loaded = sum(
                q
                for (trip, _, i), q in self._manifests[mid].items()
                if i == item and trip in request.get("trips", [])
            )
            position -= max(0, request["quantities"].get(item, 0) - recovery_loaded)
        return position

    def _dispatch(self, at_s):
        for mid, plan in list(self._pending.items()):
            origin = self._job(mid).mission.origin_id
            if all(
                v not in self._road and self._positions[v] == origin for v, _, _ in plan
            ):
                for v, _, _ in plan:
                    self._busy.pop(v, None)
                del self._pending[mid]
        self._propose_reinforcements(at_s)
        for request_id, request in list(self._requests.items()):
            if request["status"] == "approved":
                if request["kind"] == "replacement":
                    self._replacement(request_id, request, at_s)
                else:
                    self._reinforce(request_id, request, at_s)
        self._rescue_progress(at_s)
        super()._dispatch(at_s)
        for mid, rid in list(self._reinforcements.items()):
            request = self._requests[rid]
            trips = request.get("trips", [])
            if trips and all(self._loads[t].status == "loaded" for t in trips):
                job = self._job(mid)
                try:
                    path = self._network.route(
                        job.mission.origin_id,
                        job.mission.destination_id,
                        self._occupancy(),
                    )[0]
                except NoRoute:
                    request["waiting_reason"] = "road_closed"
                    continue
                for trip in trips:
                    load = self._loads[trip]
                    load.status = "en_route"
                    self._make_movement(load.vehicle_id, path, mid, trip, at_s)
                job.status = "en_route"
            if trips and all(self._loads[t].status == "completed" for t in trips):
                request.update(status="completed", completed_s=at_s)
                del self._reinforcements[mid]
                self._propose_reinforcements(at_s)

    def _finish(self, at_s):
        for v, failure in list(self._broken.items()):
            if (
                failure.get("rescue_id") is not None
                and failure["repairable"]
                and failure["due_s"] <= at_s
            ):
                self._rescues[failure["rescue_id"]]["due_s"] = (
                    at_s + failure["remaining_s"]
                )
                del self._broken[v]
                self._alerts.append(
                    {"kind": "vehicle_restored", "at_s": at_s, "vehicle_id": v}
                )
        if self._policy.automatic:
            for rescue in list(self._rescues.values()):
                v = rescue["vehicle_id"]
                if (
                    rescue["stage"] == "approach"
                    and v not in self._broken
                    and rescue["due_s"] > at_s
                    and self._drive_left[v] <= 0
                ):
                    self._automatic_failure(v, at_s)
        self._rescue_progress(at_s)
        super()._finish(at_s)
        self._rescue_progress(at_s)

    def _extra_event_times(self, cursor):
        times = super()._extra_event_times(cursor)
        times += [
            r["due_s"]
            for r in self._rescues.values()
            if r["due_s"] is not None and r["due_s"] > cursor
        ]
        if self._policy.automatic:
            times += [
                cursor + max(1, self._drive_left[r["vehicle_id"]])
                for r in self._rescues.values()
                if r["stage"] == "approach" and r["vehicle_id"] not in self._broken
            ]
        return times
