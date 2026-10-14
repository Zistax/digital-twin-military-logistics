"""Reproducible incident clocks, hidden damage, cold exposure and approvals."""

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from math import ceil, log1p
from random import Random

from .core import natural
from .supply import SupplyWarehouse
from .warehouse import command

CATEGORIES = {
    "food": 0.002,
    "cold": 0.003,
    "medical": 0.003,
    "spares": 0.001,
    "electronics": 0.005,
}


def probability(p):
    if type(p) not in (int, float) or not 0 <= p <= 1:
        raise ValueError("probability must be between 0 and 1")


def hourly_probability(p, seconds):
    probability(p)
    natural(seconds, "seconds")
    return 1 - (1 - p) ** (seconds / 3600)


@dataclass(frozen=True)
class IncidentPolicy:
    seed: int = 0
    profile: str = "regular"
    automatic: bool = False
    auto_approve: bool = False
    tolerance_s: int = 3600

    def __post_init__(self):
        natural(self.seed, "seed")
        natural(self.tolerance_s, "tolerance_s")
        if self.profile not in ("regular", "pressure", "perturbed"):
            raise ValueError("unknown profile")
        if type(self.automatic) is not bool or type(self.auto_approve) is not bool:
            raise ValueError("boolean switches required")


class IncidentWarehouse(SupplyWarehouse):
    def __init__(self, *args, incident_policy=None, categories=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._policy = incident_policy or IncidentPolicy()
        if not isinstance(self._policy, IncidentPolicy):
            raise ValueError("IncidentPolicy required")
        self._categories = dict(categories or {})
        if set(self._categories) - set(self._items) or any(
            c not in CATEGORIES for c in self._categories.values()
        ):
            raise ValueError("invalid item categories")
        if self._policy.automatic and set(self._categories) != set(self._items):
            raise ValueError("automatic damage requires category for every item")
        self._random = {}
        self._broken = {}
        self._fridge = {}
        self._cold_next = {}
        self._drive_left = {}
        self._exposure = {}
        self._hidden_bad = {}
        self._alerts = []
        self._requests = {}
        self._approval_due = {}
        self._travel_origin = {}
        if self._policy.automatic:
            for v, vehicle in self._vehicles.items():
                self._drive_left[v] = self._clock_draw("mechanical", v)
                if vehicle.cold:
                    self._cold_next[v] = self._clock_draw("cold", v)

    def _rng(self, process, key):
        stream = (process, key)
        if stream not in self._random:
            digest = sha256(repr((self._policy.seed, process, key)).encode()).digest()
            self._random[stream] = Random(digest)
        return self._random[stream]

    def _clock_draw(self, process, vehicle):
        perturbed = self._policy.profile == "perturbed"
        p = (
            (0.02 if perturbed else 0.005)
            if process == "mechanical"
            else (0.01 if perturbed else 0.002)
        )
        return max(1, ceil(self._rng(process, vehicle).expovariate(-log1p(-p) / 3600)))

    def _duration(self, process, vehicle):
        lo, hi = (1800, 7200) if self._policy.profile == "perturbed" else (900, 3600)
        return self._rng(process, vehicle).randrange(lo // 300, hi // 300 + 1) * 300

    def _damage(self, key, healthy, operation):
        if not self._policy.automatic:
            return 0
        rate = CATEGORIES[self._categories[key[2]]]
        if self._policy.profile == "perturbed":
            rate *= 3
        rng = self._rng(operation, key)
        return sum(rng.random() < rate for _ in range(healthy))

    def _supply_damage(self, order_id, item, healthy):
        return self._damage(("supply", order_id, item), healthy, "supplier-unload")

    def _cold_tolerance(self, item_id):
        tolerance = self._items[item_id].cold_tolerance_s
        return self._policy.tolerance_s if tolerance is None else tolerance

    def snapshot(self):
        state = super().snapshot()
        state.update(
            deepcopy(
                {
                    "incidents": self._alerts,
                    "requests": self._requests,
                    "broken_vehicles": self._broken,
                    "cold_exposure": self._exposure,
                    "hidden_bad": self._hidden_bad,
                }
            )
        )
        return state

    def observed_incidents(self):
        # No future approval times, hidden loss counts or recovery completion times.
        return deepcopy({"alerts": self._alerts, "requests": self._requests})

    def _request(self, kind, mission_id, at_s, **details):
        request_id = f"request-{len(self._requests) + 1}"
        self._requests[request_id] = {
            "kind": kind,
            "mission_id": mission_id,
            "created_s": at_s,
            "status": "pending",
            "decisions": [],
            **details,
        }
        if self._policy.auto_approve:
            urgent = self._job(mission_id).urgent
            lo, hi = (1, 3) if urgent else (3, 12)
            self._approval_due[request_id] = (
                at_s + self._rng("approval", request_id).randint(lo, hi) * 300
            )
        return request_id

    @command
    def decide(self, command_id, at_s, request_id, decision):
        if request_id not in self._requests or decision not in (
            "approve",
            "defer",
            "reject",
        ):
            raise ValueError("unknown request or decision")
        request = self._requests[request_id]
        if request["status"] not in ("pending", "deferred", "rejected"):
            raise ValueError("request already acted on")
        request["decisions"].append({"at_s": at_s, "decision": decision})
        request["status"] = {
            "approve": "approved",
            "defer": "deferred",
            "reject": "rejected",
        }[decision]
        self._approval_due.pop(request_id, None)

    def _make_movement(self, vehicle_id, path, mission_id, trip, at_s):
        self._travel_origin[vehicle_id] = path[0]
        super()._make_movement(vehicle_id, path, mission_id, trip, at_s)

    def _enter(self, vehicle_id, at_s):
        if vehicle_id in self._broken:
            return
        super()._enter(vehicle_id, at_s)
        if (
            self._policy.automatic
            and self._drive_left[vehicle_id] <= 0
            and self._road[vehicle_id]["end_s"] is not None
        ):
            self._automatic_failure(vehicle_id, at_s)

    def _automatic_failure(self, vehicle_id, at_s):
        rng = self._rng("failure-kind", vehicle_id)
        repairable = rng.random() < 0.8
        duration = (
            self._duration("repair", vehicle_id)
            if repairable
            else (rng.randint(24 * 12, 48 * 12) * 300)
        )
        self._fail(vehicle_id, at_s, repairable, duration)

    @command
    def breakdown(self, command_id, at_s, vehicle_id, repairable=True, duration_s=900):
        natural(duration_s, "duration_s", True)
        if type(repairable) is not bool:
            raise ValueError("repairable must be boolean")
        self._fail(vehicle_id, at_s, repairable, duration_s)

    def _fail(self, vehicle_id, at_s, repairable, duration):
        if vehicle_id in self._broken or vehicle_id not in self._road:
            raise ValueError("vehicle must be travelling and not already broken")
        movement = self._road[vehicle_id]
        if movement["end_s"] is None or movement["end_s"] <= at_s:
            raise ValueError("failure requires an active road segment")
        remaining = movement["end_s"] - at_s
        full = movement["end_s"] - movement["started_s"]
        self._broken[vehicle_id] = {
            "repairable": repairable,
            "due_s": at_s + duration,
            "remaining_s": remaining,
            "full_s": full,
            "failed_s": at_s,
            "origin": self._travel_origin[vehicle_id],
            "cargo_managed": movement["trip_id"] is None,
        }
        movement["end_s"] = None
        self._alerts.append(
            {
                "kind": "mechanical_failure",
                "at_s": at_s,
                "vehicle_id": vehicle_id,
                "repairable": repairable,
            }
        )
        if not repairable:
            if movement["trip_id"] is not None:
                self._request(
                    "replacement",
                    movement["mission_id"],
                    at_s,
                    vehicle_id=vehicle_id,
                    trip_id=movement["trip_id"],
                )
            else:
                # Empty-trip failure: abandon this allocation; moving helpers finish.
                pending = self._pending.pop(movement["mission_id"], [])
                for v, _, _ in pending:
                    if v not in self._road:
                        self._busy.pop(v, None)
        if self._policy.automatic:
            self._drive_left[vehicle_id] = self._clock_draw("mechanical", vehicle_id)

    @command
    def cold_outage(self, command_id, at_s, vehicle_id, duration_s):
        natural(duration_s, "duration_s", True)
        self._outage(vehicle_id, at_s, duration_s)

    def _outage(self, vehicle_id, at_s, duration):
        if vehicle_id not in self._vehicles or not self._vehicles[vehicle_id].cold:
            raise ValueError("refrigerated vehicle required")
        if vehicle_id in self._fridge:
            raise ValueError("outage already active")
        self._fridge[vehicle_id] = at_s + duration
        self._cold_next.pop(vehicle_id, None)
        self._alerts.append(
            {"kind": "cold_alarm", "at_s": at_s, "vehicle_id": vehicle_id}
        )

    @command
    def damage_cargo(self, command_id, at_s, trip_id, item_id, quantity):
        """Deterministic fixture injection; quantity means newly damaged units."""
        natural(quantity, "quantity", True)
        keys = [k for k in self._onboard if k[0] == trip_id and k[2] == item_id]
        if len(keys) != 1:
            raise ValueError("one known onboard batch required")
        key = keys[0]
        if quantity > self._onboard[key] - self._hidden_bad.get(key, 0):
            raise ValueError("cannot damage unavailable or already damaged cargo")
        self._hidden_bad[key] = self._hidden_bad.get(key, 0) + quantity

    @command
    def stochastic_supply(
        self, command_id, at_s, order_id, depot, quantities, expected_s
    ):
        # Whole-supply incomplete event; each article gets an independent fraction.
        perturbed = self._policy.profile == "perturbed"
        rng = self._rng("supplier", order_id)
        delay = 0
        if rng.random() < (0.3 if perturbed else 0.1):
            lo, hi = (4 * 3600, 24 * 3600) if perturbed else (3600, 6 * 3600)
            delay = rng.randint(lo // 300, hi // 300) * 300
        actual = dict(quantities)
        if rng.random() < (0.15 if perturbed else 0.05):
            lo, hi = (0.6, 0.9) if perturbed else (0.8, 0.95)
            actual = {
                i: int(q * rng.uniform(lo, hi)) for i, q in sorted(quantities.items())
            }
        SupplyWarehouse.order_supply.__wrapped__(
            self,
            command_id,
            at_s,
            order_id,
            depot,
            quantities,
            expected_s,
            expected_s + delay,
            actual,
        )

    def _place_reorder(self, at_s, order_id, depot, quantities, expected_s):
        if self._policy.automatic:
            IncidentWarehouse.stochastic_supply.__wrapped__(
                self, "auto", at_s, order_id, depot, quantities, expected_s
            )
        else:
            super()._place_reorder(at_s, order_id, depot, quantities, expected_s)

    def _on_interval(self, start_s, end_s):
        super()._on_interval(start_s, end_s)
        duration = end_s - start_s
        if self._policy.automatic:
            for v, movement in self._road.items():
                if movement["end_s"] is not None and v not in self._broken:
                    self._drive_left[v] -= duration
        for key, q in self._onboard.items():
            vehicle = self._loads[key[0]].vehicle_id
            if q and self._items[key[2]].cold and vehicle in self._fridge:
                self._exposure[key] = self._exposure.get(key, 0) + duration
                if self._exposure[key] > self._cold_tolerance(key[2]):
                    self._hidden_bad[key] = q

    def _inspect_due(self, at_s):
        # Reclassify only units selected for this visit; unknown losses become visible.
        for trip, op in sorted(self._active.items(), key=lambda pair: str(pair[0])):
            if op["kind"] != "unload" or op["end_s"] != at_s:
                continue
            old_selection = op["selection"]
            op["selection"] = {}  # release space before reclassifying at inspection
            for key, (planned_good, planned_bad) in old_selection.items():
                total_bad = self._hidden_bad.get(key, self._bad_onboard.get(key, 0))
                unseen = max(0, total_bad - self._bad_onboard.get(key, 0))
                newly_seen = min(planned_good, unseen)
                good = planned_good - newly_seen
                new_damage = self._damage(key, good, "unload")
                good -= new_damage
                total_bad += new_damage
                bad = planned_bad + newly_seen + new_damage
                item = self._items[key[2]]
                room = max(0, int(self._space(op["depot"], item.cold, True) // item.m3))
                moved_bad = min(bad, room)
                self._bad_onboard[key] = total_bad
                self._hidden_bad[key] = total_bad - moved_bad
                if good + moved_bad:
                    op["selection"][key] = (good, moved_bad)
                self._alerts.append(
                    {
                        "kind": "inspection",
                        "at_s": at_s,
                        "trip_id": trip,
                        "item_id": key[2],
                        "accepted": good,
                        "unusable_unloaded": moved_bad,
                    }
                )

    def _finish(self, at_s):
        for vehicle_id, end in list(self._fridge.items()):
            if end == at_s:
                del self._fridge[vehicle_id]
                self._alerts.append(
                    {"kind": "cold_restored", "at_s": at_s, "vehicle_id": vehicle_id}
                )
                if self._policy.automatic:
                    self._cold_next[vehicle_id] = at_s + self._clock_draw(
                        "cold", vehicle_id
                    )
        for vehicle_id, due in list(self._cold_next.items()):
            if due == at_s:
                self._outage(
                    vehicle_id, at_s, self._duration("cold-duration", vehicle_id)
                )
        for vehicle_id, failure in list(self._broken.items()):
            if failure["due_s"] <= at_s and (
                failure["repairable"] or failure["cargo_managed"]
            ):
                if failure["repairable"]:
                    movement = self._road[vehicle_id]
                    movement["end_s"] = at_s + failure["remaining_s"]
                    movement["started_s"] = movement["end_s"] - failure["full_s"]
                else:
                    self._road.pop(vehicle_id, None)
                    self._positions[vehicle_id] = failure["origin"]
                    self._busy.pop(vehicle_id, None)
                del self._broken[vehicle_id]
                self._alerts.append(
                    {"kind": "vehicle_restored", "at_s": at_s, "vehicle_id": vehicle_id}
                )
        if self._policy.automatic:
            for v, movement in list(self._road.items()):
                if (
                    v not in self._broken
                    and self._drive_left[v] <= 0
                    and movement["end_s"] is not None
                    and movement["end_s"] > at_s
                ):
                    self._automatic_failure(v, at_s)
        for request_id, due in list(self._approval_due.items()):
            if due == at_s:
                IncidentWarehouse.decide.__wrapped__(
                    self, "batch", at_s, request_id, "approve"
                )
        loading = [
            t
            for t, op in self._active.items()
            if op["kind"] == "load" and op["end_s"] == at_s
        ]
        self._inspect_due(at_s)
        super()._finish(at_s)
        for trip in loading:
            for key, quantity in self._onboard.items():
                if key[0] == trip:
                    self._exposure[key] = 0
                    self._hidden_bad[key] = self._damage(key, quantity, "load")
        # Release helpers whose abandoned empty assignment has finished.
        for v, busy in list(self._busy.items()):
            if (
                isinstance(busy, tuple)
                and busy[0] == "empty"
                and v not in self._road
                and v not in self._broken
                and not any(
                    v == entry[0] for p in self._pending.values() for entry in p
                )
            ):
                del self._busy[v]

    def _extra_event_times(self, cursor):
        times = super()._extra_event_times(cursor)
        times += list(self._fridge.values()) + list(self._cold_next.values())
        times += list(self._approval_due.values())
        times += [
            f["due_s"]
            for f in self._broken.values()
            if f["due_s"] > cursor and (f["repairable"] or f["cargo_managed"])
        ]
        if self._policy.automatic:
            for v, movement in self._road.items():
                if movement["end_s"] is not None and v not in self._broken:
                    times.append(cursor + max(1, self._drive_left[v]))
        for key, q in self._onboard.items():
            if (
                q > self._hidden_bad.get(key, 0)
                and self._items[key[2]].cold
                and self._loads[key[0]].vehicle_id in self._fridge
            ):
                times.append(
                    cursor
                    + max(
                        1, self._cold_tolerance(key[2]) - self._exposure.get(key, 0) + 1
                    )
                )
        return [t for t in times if t > cursor]
