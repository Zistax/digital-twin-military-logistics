"""Observable planning context captured alongside each feature observation."""

from copy import deepcopy


def validate_context_journal(contexts, events):
    """Verify observable snapshots at the exact journal ordinal in one pass."""
    pending = {}
    for row in contexts:
        pending.setdefault(row["journal_event_id"], []).append(row)
    state = {}
    for ordinal, event in enumerate(events):
        if event["event_id"] != f"state:{ordinal}":
            raise ValueError("nonsequential journal cursor")
        state.update(event["changes"])
        for row in pending.pop(event["event_id"], []):
            if event["observed_s"] > row["observed_s"]:
                raise ValueError("context references a future journal event")
            context = row["context"]
            for depot, value in context["depots"].items():
                stock = state["stock"][depot]
                if value["stock"] != stock:
                    raise ValueError("context stock differs from journal")
                for item, available in value["available"].items():
                    reserved = sum(
                        job["reserved"].get(item, 0)
                        for job in state["missions"].values()
                        if job["mission"]["origin_id"] == depot
                    )
                    if available != stock.get(item, 0) - reserved:
                        raise ValueError("context availability differs from journal")
                if value["berths_used"] != sum(
                    op["depot"] == depot for op in state["operations"].values()
                ) or value["queue_size"] != sum(
                    op["depot"] == depot for op in state["queue"].values()
                ):
                    raise ValueError("context operations differ from journal")
            if set(context["fleet"]) != set(state["fleet"]):
                raise ValueError("context fleet differs from journal")
            for vehicle, value in context["fleet"].items():
                actual = state["fleet"][vehicle]
                if value["position"] != actual["position"] or value["busy"] != (
                    actual["assignment"] is not None
                ):
                    raise ValueError("context vehicle status differs from journal")
            for supply, value in context["supplies"].items():
                if value != state["supplies"].get(supply):
                    raise ValueError("context supply differs from journal")
            if context["environment"] != state.get("environment"):
                raise ValueError("context environment differs from journal")
    if pending:
        raise ValueError("orphan context journal cursor")


def observation_context(w, observation):
    origin = (
        w._job(observation["mission_id"]).mission.origin_id
        if observation["feature_version"] == "rolling-v1"
        else observation["features"]["origin_id"]
    )
    destination = (
        w._job(observation["mission_id"]).mission.destination_id
        if observation["feature_version"] == "rolling-v1"
        else observation["features"]["destination_id"]
    )
    depots = (origin, destination)
    items = {line["item_id"] for line in observation["features"]["lines"]}
    supplies = {
        sid: row
        for sid, row in w.observed_supplies().items()
        if row["depot"] in depots
        and row["status"] in ("expected", "waiting")
        and any(row["ordered"].get(item, 0) for item in items)
    }
    value = {
        "schema_version": 1,
        "context_version": "planning-context-v1",
        "simulation_id": observation["simulation_id"],
        "mission_id": observation["mission_id"],
        "observation_id": observation["observation_id"],
        "observed_s": observation["observed_s"],
        "observed_utc": observation["observed_utc"],
        "journal_event_id": f"state:{len(w._journal.records)-1}",
        "context": {
            "depots": {
                d: {
                    "stock": w._stock[d],
                    "available": {i: w.available(d, i) for i in w._items},
                    "opening_now": w._operations[d].calendar.is_open(
                        w._epoch, w._clock
                    ),
                    "next_calendar_change_s": w._operations[d].calendar.next_change(
                        w._epoch, w._clock
                    ),
                    "berths": w._operations[d].berths,
                    "berths_used": sum(op["depot"] == d for op in w._active.values()),
                    "queue_size": sum(op["depot"] == d for op in w._queue.values()),
                }
                for d in depots
            },
            "fleet": {
                v: {
                    "position": w._positions[v],
                    "busy": v in w._busy,
                    "cold": vehicle.cold,
                    "max_kg": str(vehicle.max_kg),
                    "max_m3": str(vehicle.max_m3),
                }
                for v, vehicle in w._vehicles.items()
            },
            "supplies": supplies,
            "environment": (
                w.observed_environment() if hasattr(w, "observed_environment") else None
            ),
        },
    }
    from .journal import normalize

    return normalize(deepcopy(value))


def validate_context(row, observation):
    fields = {
        "schema_version",
        "context_version",
        "simulation_id",
        "mission_id",
        "observation_id",
        "observed_s",
        "observed_utc",
        "context",
        "journal_event_id",
    }
    if (
        set(row) != fields
        or type(row["schema_version"]) is not int
        or row["schema_version"] != 1
        or row["context_version"] != "planning-context-v1"
    ):
        raise ValueError("unknown context contract")
    for field in (
        "simulation_id",
        "mission_id",
        "observation_id",
        "observed_s",
        "observed_utc",
    ):
        if row[field] != observation[field]:
            raise ValueError("context cutoff or identity mismatch")
    if set(row["context"]) != {"depots", "fleet", "supplies", "environment"}:
        raise ValueError("unapproved planning context")
    for supply in row["context"]["supplies"].values():
        allowed = {
            "depot",
            "ordered",
            "expected_s",
            "status",
            "created_s",
            "remaining",
            "received",
            "unusable",
            "bad_remaining",
            "not_delivered",
            "arrived_s",
            "closed_s",
        }
        if not set(supply) <= allowed:
            raise ValueError("unapproved supplier context")
        if "actual_s" in supply or "actual" in supply:
            raise ValueError("hidden supplier outcome in context")
        if supply["status"] == "expected" and any(
            field in supply for field in ("remaining", "not_delivered", "arrived_s")
        ):
            raise ValueError("future arrival details in context")
    from .core import natural

    for depot in row["context"]["depots"].values():
        if set(depot) != {
            "stock",
            "available",
            "opening_now",
            "next_calendar_change_s",
            "berths",
            "berths_used",
            "queue_size",
        }:
            raise ValueError("unapproved depot context")
        for quantities in (depot["stock"], depot["available"]):
            for quantity in quantities.values():
                natural(quantity, "context quantity")
        for field in ("berths", "berths_used", "queue_size", "next_calendar_change_s"):
            natural(depot[field], field)
        if (
            type(depot["opening_now"]) is not bool
            or depot["berths_used"] > depot["berths"]
        ):
            raise ValueError("invalid berth/opening context")
    for vehicle in row["context"]["fleet"].values():
        if set(vehicle) != {"position", "busy", "cold", "max_kg", "max_m3"}:
            raise ValueError("unapproved vehicle context")
        if type(vehicle["busy"]) is not bool or type(vehicle["cold"]) is not bool:
            raise ValueError("boolean vehicle flags required")
    environment = row["context"]["environment"]
    if environment is not None:
        if (
            set(environment) != {"observed_s", "traffic", "weather", "forecast"}
            or environment["observed_s"] > row["observed_s"]
        ):
            raise ValueError("future or unapproved environment context")
        forecast = environment["forecast"]
        if forecast and (
            set(forecast) != {"version", "model", "issued_s", "horizon_s", "values"}
            or forecast["issued_s"] > row["observed_s"]
        ):
            raise ValueError("forecast issued after context cutoff")
