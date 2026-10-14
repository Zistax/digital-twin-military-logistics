"""Immutable serialized state transitions, safe to share in rollback copies."""

from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta
import json


def normalize(value):
    if isinstance(value, dict):
        return {
            json.dumps(list(key)) if isinstance(key, tuple) else str(key): normalize(v)
            for key, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [normalize(v) for v in value]
    return value


class Journal:
    def __init__(self):
        self.records = ()
        self.state = {}

    def __deepcopy__(self, memo):
        clone = type(self)()
        clone.records = self.records
        clone.state = deepcopy(self.state, memo)
        memo[id(self)] = clone
        return clone

    def capture(self, w, at_s):
        state = {
            "stock": w._stock,
            "quarantine": w._quarantine,
            "received": w._received,
            "removed": w._removed,
            "onboard": {json.dumps(list(key)): q for key, q in w._onboard.items()},
            "missions": {
                mid: {
                    "mission": asdict(job.mission),
                    "urgent": job.urgent,
                    "status": job.status,
                    "reserved": job.reserved,
                }
                for mid, job in w._jobs.items()
            },
            "fleet": {
                v: {"position": w._positions[v], "assignment": w._busy.get(v)}
                for v in w._vehicles
            },
            "operations": {str(key): op for key, op in w._active.items()},
            "queue": {
                trip: {**row, "reason": w._reason(trip, at_s)}
                for trip, row in w._queue.items()
            },
            "supplies": w.observed_supplies(),
            "incidents": w.observed_incidents(),
            "local": {rid: r for rid, r in w._local.items() if r["due_s"] <= at_s},
            "environment": (
                w.observed_environment() if hasattr(w, "observed_environment") else None
            ),
            "roads": normalize(w._network.conditions),
        }
        normalized = json.loads(
            json.dumps(normalize(state), sort_keys=True, default=str, allow_nan=False)
        )
        changed = {k: v for k, v in normalized.items() if self.state.get(k) != v}
        if not changed:
            return
        event = {
            "schema_version": 1,
            "event_id": f"state:{len(self.records)}",
            "simulation_id": w.simulation_id,
            "occurred_s": at_s,
            "observed_s": at_s,
            "observed_utc": (w._epoch + timedelta(seconds=at_s)).isoformat(),
            "changes": changed,
        }
        self.records += (json.dumps(event, sort_keys=True, allow_nan=False),)
        self.state = normalized

    def export(self):
        return [json.loads(row) for row in self.records]


def replay_journal(events, simulation_id, cutoff_s):
    state, seen, last = {}, set(), -1
    allowed = {
        "stock",
        "quarantine",
        "received",
        "removed",
        "onboard",
        "missions",
        "fleet",
        "operations",
        "queue",
        "supplies",
        "incidents",
        "local",
        "environment",
        "roads",
    }
    for event in events:
        if event["observed_s"] > cutoff_s:
            continue
        fields = {
            "schema_version",
            "event_id",
            "simulation_id",
            "occurred_s",
            "observed_s",
            "observed_utc",
            "changes",
        }
        from .core import natural

        natural(event["occurred_s"], "occurred_s")
        natural(event["observed_s"], "observed_s")
        if (
            set(event) != fields
            or type(event["schema_version"]) is not int
            or event["schema_version"] != 1
            or event["simulation_id"] != simulation_id
            or event["event_id"] in seen
            or event["occurred_s"] != event["observed_s"]
            or event["observed_s"] < last
            or not set(event["changes"]) <= allowed
        ):
            raise ValueError("invalid operational journal event")
        last = event["observed_s"]
        seen.add(event["event_id"])
        state.update(deepcopy(event["changes"]))
        if "received" in state:
            for quantities in (state["received"], state["removed"], state["onboard"]):
                for quantity in quantities.values():
                    natural(quantity, "journal quantity")
            for item, quantity in state["received"].items():
                total = sum(stock.get(item, 0) for stock in state["stock"].values())
                total += sum(
                    stock.get(item, 0) for stock in state["quarantine"].values()
                )
                total += sum(
                    q
                    for key, q in state["onboard"].items()
                    if json.loads(key)[2] == item
                )
                if total + state["removed"][item] != quantity:
                    raise ValueError("journal physical conservation violation")
        for stock in list(state.get("stock", {}).values()) + list(
            state.get("quarantine", {}).values()
        ):
            if any(type(q) is not int or q < 0 for q in stock.values()):
                raise ValueError("negative or noninteger journal stock")
            if not set(stock) <= set(state["received"]):
                raise ValueError("unknown journal item")
        for depot, stock in state.get("stock", {}).items():
            reservations = {}
            for job in state.get("missions", {}).values():
                if job["mission"]["origin_id"] == depot:
                    for item, q in job["reserved"].items():
                        natural(q, "reservation")
                        reservations[item] = reservations.get(item, 0) + q
            if any(q > stock.get(item, 0) for item, q in reservations.items()):
                raise ValueError("journal reservations exceed physical stock")
    return state
