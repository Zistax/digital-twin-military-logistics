"""External supply, local consumption and capacity-limited inventory control."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
from hashlib import sha256
from random import Random
from zoneinfo import ZoneInfo

from .core import identifier, natural
from .operations import OperationsWarehouse
from .transport import TransportWarehouse
from .warehouse import command, measure


@dataclass(frozen=True)
class ReorderRule:
    daily_demand: Decimal
    trigger_days: Decimal
    target_days: Decimal
    lead_s: int

    def __post_init__(self):
        for name in ("daily_demand", "trigger_days", "target_days"):
            measure(getattr(self, name), name)
        if self.target_days <= self.trigger_days:
            raise ValueError("target must exceed trigger")
        natural(self.lead_s, "lead_s", True)


class SupplyWarehouse(TransportWarehouse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._supplies = {}
        self._local = {}
        self._rules = {}
        self._next_reorder = None
        self._reorder_interval = 3600
        self._supply_sequence = 0
        self._supply_log = []
        self._consumed = dict.fromkeys(self._items, 0)
        self._supply_wait = {}
        self._mission_wait = {}

    def snapshot(self):
        state = super().snapshot()
        state.update(
            deepcopy(
                {
                    "supplies": self._supplies,
                    "local_requests": self._local,
                    "supply_log": self._supply_log,
                    "consumed": self._consumed,
                    "supply_wait_seconds": self._supply_wait,
                    "mission_wait_seconds": self._mission_wait,
                }
            )
        )
        return state

    def observed_supplies(self):
        """Current operator view; no sampled arrival time or quantities before
        arrival."""
        result = {}
        for order_id, supply in self._supplies.items():
            fields = ("depot", "ordered", "expected_s", "status", "created_s")
            view = {field: supply[field] for field in fields}
            if supply["status"] != "expected":
                view.update(
                    {
                        field: supply[field]
                        for field in (
                            "remaining",
                            "received",
                            "unusable",
                            "bad_remaining",
                            "not_delivered",
                        )
                    }
                )
                view["arrived_s"] = supply["actual_s"]
                if "closed_s" in supply:
                    view["closed_s"] = supply["closed_s"]
            result[order_id] = deepcopy(view)
        return result

    def _check(self):
        super()._check()
        for supply in getattr(self, "_supplies", {}).values():
            if supply["status"] == "expected":
                continue
            for item, actual in supply["actual"].items():
                remaining = supply["remaining"][item]
                received = supply["received"][item]
                if (
                    remaining + received != actual
                    or not 0 <= supply["bad_remaining"][item] <= remaining
                    or not 0 <= supply["unusable"][item] <= received
                ):
                    raise ValueError("external supply conservation violated")

    def _validate_depot_items(self, depot, quantities):
        self._quantities(quantities)
        if depot not in self._stores:
            raise ValueError("unknown depot")
        for item in quantities:
            config = self._stores[depot]
            capacity = config.cold_m3 if self._items[item].cold else config.ordinary_m3
            if capacity < self._items[item].m3:
                raise ValueError("incompatible item/depot")

    @command
    def order_supply(
        self,
        command_id,
        at_s,
        order_id,
        depot,
        quantities,
        expected_s,
        actual_s=None,
        actual_quantities=None,
    ):
        identifier(order_id)
        self._validate_depot_items(depot, quantities)
        natural(expected_s, "expected_s")
        actual_s = expected_s if actual_s is None else actual_s
        natural(actual_s, "actual_s")
        if expected_s < at_s or actual_s < at_s or order_id in self._supplies:
            raise ValueError("past or duplicated order")
        actual = dict(quantities) if actual_quantities is None else actual_quantities
        if not isinstance(actual, dict) or set(actual) - set(quantities):
            raise ValueError("invalid actual supply")
        actual = {i: actual.get(i, 0) for i in quantities}
        for item, q in actual.items():
            natural(q, "actual quantity")
            if q > quantities[item]:
                raise ValueError("actual exceeds ordered quantity")
        self._supplies[order_id] = {
            "depot": depot,
            "ordered": dict(quantities),
            "expected_s": expected_s,
            "actual_s": actual_s,
            "actual": dict(actual),
            "status": "expected",
            "remaining": {},
            "received": dict.fromkeys(quantities, 0),
            "bad_remaining": dict.fromkeys(quantities, 0),
            "unusable": dict.fromkeys(quantities, 0),
            "not_delivered": {},
            "created_s": at_s,
        }
        self._supply_wait[order_id] = dict.fromkeys(("opening", "berth", "space"), 0)

    @command
    def local_request(
        self, command_id, at_s, request_id, depot, quantities, due_s=None
    ):
        identifier(request_id)
        self._validate_depot_items(depot, quantities)
        due_s = at_s if due_s is None else due_s
        natural(due_s, "due_s")
        if request_id in self._local or due_s < at_s:
            raise ValueError("duplicate request or past due time")
        self._local[request_id] = {
            "depot": depot,
            "requested": dict(quantities),
            "remaining": dict(quantities),
            "due_s": due_s,
            "completed_s": None,
            "wait_s": 0,
            "withdrawals": [],
        }

    @command
    def schedule_local_days(
        self, command_id, at_s, depot, daily_shipments, days, seed=0
    ):
        natural(days, "days", True)
        natural(seed, "seed")
        if depot not in self._stores or not isinstance(daily_shipments, dict):
            raise ValueError("invalid local demand configuration")
        for item, value in daily_shipments.items():
            if item not in self._items:
                raise ValueError("unknown item")
            measure(value, "expected shipments")
        calendar = self._operations[depot].calendar
        zone = ZoneInfo(calendar.timezone_name)
        first_day = (self._epoch + timedelta(seconds=at_s)).astimezone(zone).date()
        opening = min(start for _, start, _ in calendar.windows)
        generated = []
        for offset in range(days):
            day = first_day + timedelta(days=offset)
            instant = datetime.combine(day, time()) + timedelta(seconds=opening)
            instant = instant.replace(tzinfo=zone).astimezone(timezone.utc)
            due = int((instant - self._epoch).total_seconds())
            if due < at_s:
                continue
            rng_seed = sha256(f"{seed}|{depot}|{day.isoformat()}".encode()).digest()
            rng = Random(rng_seed)
            quantities = {}
            for item, daily in sorted(daily_shipments.items()):
                fraction = Decimal(str(rng.uniform(0.1, 0.3)))
                q = int((daily * fraction).to_integral_value(rounding=ROUND_CEILING))
                if q:
                    quantities[item] = q
            if quantities:
                request_id = f"daily:{depot}:{day.isoformat()}"
                SupplyWarehouse.local_request.__wrapped__(
                    self, command_id, at_s, request_id, depot, quantities, due
                )
                generated.append(request_id)
        return generated

    @command
    def configure_reorder(self, command_id, at_s, rules, interval_s=3600):
        natural(interval_s, "interval_s", True)
        for key, rule in rules.items():
            if (
                not isinstance(key, tuple)
                or len(key) != 2
                or not isinstance(rule, ReorderRule)
            ):
                raise ValueError("rules keyed by (depot, item) required")
            self._validate_depot_items(key[0], {key[1]: 1})
        self._rules = dict(rules)
        self._reorder_interval = interval_s
        self._next_reorder = at_s if rules else None

    def _incoming(self, depot, item):
        total = 0
        for supply in self._supplies.values():
            if supply["depot"] == depot:
                if supply["status"] == "expected":
                    total += supply["ordered"].get(item, 0)
                elif supply["status"] == "waiting":
                    total += supply["remaining"].get(item, 0) - supply[
                        "bad_remaining"
                    ].get(item, 0)
        # Count committed internal cargo once, including loading plans.
        for trip, load in self._loads.items():
            if self._job(load.mission_id).mission.destination_id == depot:
                delivered = sum(
                    e.accepted + e.unusable
                    for e in self._events
                    if e.trip_id == trip and e.item_id == item
                )
                total += max(0, load.quantities.get(item, 0) - delivered)
        return total

    def inventory_position(self, depot, item, at_s=None):
        if depot not in self._stores or item not in self._items:
            raise ValueError("unknown depot/item")
        now = self._engine_s if at_s is None else at_s
        demand = 0
        for job in self._jobs.values():
            if job.mission.origin_id != depot or job.status not in (
                "waiting",
                "loading",
            ):
                continue
            requested = sum(
                line.requested for line in job.mission.lines if line.item_id == item
            )
            loaded = sum(
                q
                for (_, _, i), q in self._manifests[job.mission.mission_id].items()
                if i == item
            )
            demand += max(0, requested - loaded)
        demand += sum(
            r["remaining"].get(item, 0)
            for r in self._local.values()
            if r["depot"] == depot and r["due_s"] <= now
        )
        return self._stock[depot].get(item, 0) + self._incoming(depot, item) - demand

    def _consume(self, at_s):
        for request_id, request in sorted(
            self._local.items(), key=lambda pair: (pair[1]["due_s"], pair[0])
        ):
            depot = request["depot"]
            if request["due_s"] <= at_s and request["completed_s"] is None:
                request["wait_s"] = at_s - request["due_s"]
            if (
                request["due_s"] > at_s
                or request["completed_s"] is not None
                or not self._operations[depot].calendar.is_open(self._epoch, at_s)
            ):
                continue
            for item, q in request["remaining"].items():
                take = min(q, self.available(depot, item))
                if take:
                    self._stock[depot][item] -= take
                    request["remaining"][item] -= take
                    self._removed[item] += take
                    self._consumed[item] += take
                    request["withdrawals"].append(
                        {"at_s": at_s, "item": item, "quantity": take}
                    )
            if not any(request["remaining"].values()):
                request["completed_s"] = at_s

    def _allocate(self, at_s):
        # New goods: urgent missions -> local backlog -> ordinary missions.
        urgent = sorted(
            (mid for mid in self._scheduled if self._job(mid).urgent),
            key=lambda mid: (self._job(mid).mission.deadline_s, self._job(mid).order),
        )
        for mid in urgent:
            job = self._job(mid)
            if job.mission.start_s <= at_s and job.status in ("waiting", "loading"):
                previous = dict(job.reserved)
                result = OperationsWarehouse.reserve.__wrapped__(
                    self, "auto", at_s, mid
                )
                if previous != job.reserved or result["transfers"]:
                    self._transport_log.append(
                        {
                            "kind": "reservation",
                            "at_s": at_s,
                            "mission_id": mid,
                            **result,
                        }
                    )
        self._consume(at_s)
        super()._allocate(at_s)

    def _space(self, depot, cold, quarantine):
        free = super()._space(depot, cold, quarantine)
        for op in self._active.values():
            if op["kind"] == "supply" and op["depot"] == depot:
                selection = (
                    op.get("bad_selection", {}) if quarantine else op["selection"]
                )
                free -= sum(
                    (
                        self._items[i].m3 * q
                        for i, q in selection.items()
                        if self._items[i].cold == cold
                    ),
                    Decimal(0),
                )
        return free

    def _dispatch_supplies(self, at_s):
        for order_id, supply in sorted(
            self._supplies.items(), key=lambda pair: (pair[1]["actual_s"], pair[0])
        ):
            if supply["status"] != "waiting":
                continue
            key = ("supply", order_id)
            depot = supply["depot"]
            if (
                key in self._active
                or not self._operations[depot].calendar.is_open(self._epoch, at_s)
                or sum(op["depot"] == depot for op in self._active.values())
                >= self._operations[depot].berths
            ):
                continue
            free = {cold: self._space(depot, cold, False) for cold in (False, True)}
            bad_free = {cold: self._space(depot, cold, True) for cold in (False, True)}
            selected = {}
            bad_selected = {}
            for item, q in sorted(supply["remaining"].items()):
                config = self._items[item]
                bad = supply["bad_remaining"][item]
                take = min(q - bad, int(free[config.cold] // config.m3))
                if take:
                    selected[item] = take
                    free[config.cold] -= take * config.m3
                take_bad = min(bad, int(bad_free[config.cold] // config.m3))
                if take_bad:
                    bad_selected[item] = take_bad
                    bad_free[config.cold] -= take_bad * config.m3
            if not selected and not bad_selected:
                continue
            seconds = 300 + sum(
                self._items[i].handling_s * q
                for part in (selected, bad_selected)
                for i, q in part.items()
            )
            if any(self._items[i].cold for i in selected.keys() | bad_selected.keys()):
                seconds += 300
            duration = ((seconds + self.tick_s - 1) // self.tick_s) * self.tick_s
            self._active[key] = {
                "kind": "supply",
                "depot": depot,
                "selection": selected,
                "bad_selection": bad_selected,
                "start_s": at_s,
                "end_s": at_s + duration,
            }

    def _reorder(self, at_s):
        if self._next_reorder is None or at_s < self._next_reorder:
            return
        self._next_reorder = at_s + self._reorder_interval
        for (depot, item), rule in sorted(self._rules.items()):
            position = self.inventory_position(depot, item, at_s)
            if (
                rule.daily_demand == 0
                or position >= rule.daily_demand * rule.trigger_days
            ):
                continue
            wanted = int(
                (rule.daily_demand * rule.target_days - position).to_integral_value(
                    rounding=ROUND_CEILING
                )
            )
            cold = self._items[item].cold
            store = self._stores[depot]
            capacity = store.cold_m3 if cold else store.ordinary_m3
            committed = sum(
                (
                    config.m3
                    * (self._stock[depot].get(i, 0) + self._incoming(depot, i))
                    for i, config in self._items.items()
                    if config.cold == cold
                ),
                Decimal(0),
            )
            fits = max(0, int((capacity - committed) // self._items[item].m3))
            quantity = min(wanted, fits)
            if quantity < wanted:
                self._supply_log.append(
                    {
                        "kind": "reorder_capacity_limited",
                        "at_s": at_s,
                        "depot": depot,
                        "item": item,
                        "wanted": wanted,
                        "ordered": quantity,
                    }
                )
            if quantity:
                self._supply_sequence += 1
                order_id = f"reorder-{self._supply_sequence}"
                while order_id in self._supplies:
                    self._supply_sequence += 1
                    order_id = f"reorder-{self._supply_sequence}"
                self._place_reorder(
                    at_s, order_id, depot, {item: quantity}, at_s + rule.lead_s
                )
                self._supply_log.append(
                    {
                        "kind": "reorder",
                        "at_s": at_s,
                        "order_id": order_id,
                        "position": position,
                    }
                )

    def _place_reorder(self, at_s, order_id, depot, quantities, expected_s):
        SupplyWarehouse.order_supply.__wrapped__(
            self, "auto", at_s, order_id, depot, quantities, expected_s
        )

    def _dispatch(self, at_s):
        super()._dispatch(at_s)
        self._dispatch_supplies(at_s)
        self._reorder(at_s)

    def _finish(self, at_s):
        # External vehicles are outside the physical ledger until accepted unload.
        for order_id, supply in self._supplies.items():
            if supply["status"] == "expected" and supply["actual_s"] == at_s:
                supply["remaining"] = dict(supply["actual"])
                supply["not_delivered"] = {
                    i: q - supply["actual"][i] for i, q in supply["ordered"].items()
                }
                supply["status"] = (
                    "waiting" if any(supply["remaining"].values()) else "closed"
                )
                if supply["status"] == "closed":
                    supply["closed_s"] = at_s
                self._supply_log.append(
                    {
                        "kind": "supply_arrival",
                        "order_id": order_id,
                        "at_s": at_s,
                        "not_delivered": dict(supply["not_delivered"]),
                    }
                )
        for key, op in list(self._active.items()):
            if op["kind"] != "supply" or op["end_s"] != at_s:
                continue
            del self._active[key]
            supply = self._supplies[key[1]]
            accepted, unusable = {}, {}
            for item in sorted(op["selection"].keys() | op["bad_selection"].keys()):
                q = op["selection"].get(item, 0)
                damage = self._supply_damage(key[1], item, q) if q else 0
                good = q - damage
                supply["bad_remaining"][item] += damage
                config = self._items[item]
                room = max(
                    0, int(self._space(op["depot"], config.cold, True) // config.m3)
                )
                bad = min(op["bad_selection"].get(item, 0) + damage, room)
                stock = self._stock[op["depot"]]
                stock[item] = stock.get(item, 0) + good
                quarantine = self._quarantine[op["depot"]]
                quarantine[item] = quarantine.get(item, 0) + bad
                if bad:
                    self._quarantine_entries.append(
                        (op["depot"], item, bad, at_s + 86400)
                    )
                self._received[item] += good + bad
                supply["remaining"][item] -= good + bad
                supply["bad_remaining"][item] -= bad
                supply["received"][item] += good + bad
                supply["unusable"][item] += bad
                accepted[item], unusable[item] = good, bad
            if not any(supply["remaining"].values()):
                supply["status"] = "closed"
                supply["closed_s"] = at_s
            self._supply_log.append(
                {
                    **op,
                    "kind": "supply_unload",
                    "order_id": key[1],
                    "accepted": accepted,
                    "unusable": unusable,
                    "overtime_s": self._operations[op["depot"]].calendar.closed_seconds(
                        self._epoch, op["start_s"], at_s
                    ),
                }
            )
        super()._finish(at_s)

    def _supply_damage(self, order_id, item, healthy):
        return 0

    def _supply_wait_reason(self, order_id, at_s):
        supply = self._supplies[order_id]
        depot = supply["depot"]
        if not self._operations[depot].calendar.is_open(self._epoch, at_s):
            return "opening"
        if (
            sum(op["depot"] == depot for op in self._active.values())
            >= self._operations[depot].berths
        ):
            return "berth"
        return "space"

    def _on_interval(self, start_s, end_s):
        super()._on_interval(start_s, end_s)
        duration = end_s - start_s
        for order_id, supply in self._supplies.items():
            if (
                supply["status"] == "waiting"
                and ("supply", order_id) not in self._active
            ):
                reason = self._supply_wait_reason(order_id, start_s)
                self._supply_wait[order_id][reason] += duration
        for mid, reason in self._allocation_wait.items():
            if self._job(mid).status in ("waiting", "loading"):
                waits = self._mission_wait.setdefault(mid, {})
                waits[reason] = waits.get(reason, 0) + duration

    def _extra_event_times(self, cursor):
        times = super()._extra_event_times(cursor)
        times += [
            s["actual_s"]
            for s in self._supplies.values()
            if s["status"] == "expected" and s["actual_s"] > cursor
        ]
        for r in self._local.values():
            if r["completed_s"] is None:
                if r["due_s"] > cursor:
                    times.append(r["due_s"])
                else:
                    times.append(
                        self._operations[r["depot"]].calendar.next_change(
                            self._epoch, cursor
                        )
                    )
        for s in self._supplies.values():
            if s["status"] == "waiting":
                times.append(
                    self._operations[s["depot"]].calendar.next_change(
                        self._epoch, cursor
                    )
                )
        if self._next_reorder is not None and self._next_reorder > cursor:
            times.append(self._next_reorder)
        return times
