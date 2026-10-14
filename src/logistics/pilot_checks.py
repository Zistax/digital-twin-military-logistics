"""Operational checkpoints and explicit reasons for open pilot missions."""

from copy import deepcopy


def operational_checkpoint(w, at_s):
    return deepcopy(
        {
            "at_s": at_s,
            "stock": w._stock,
            "reservations": {mid: job.reserved for mid, job in w._jobs.items()},
            "queues": {
                trip: {
                    "mission_id": w._loads[trip].mission_id,
                    "depot": row["depot"],
                    "kind": row["kind"],
                    "reason": w._reason(trip, at_s),
                }
                for trip, row in w._queue.items()
            },
            "berths": [
                {
                    "depot": op["depot"],
                    "kind": op["kind"],
                    "start_s": op["start_s"],
                    "planned_end_s": op["end_s"],
                }
                for op in w._active.values()
            ],
            "supplies": w.observed_supplies(),
            "allocation_reasons": w._allocation_wait,
            "alerts": w.observed_incidents()["alerts"],
            "requests": w.observed_incidents()["requests"],
        }
    )


def explain_open_mission(w, mid, at_s):
    reasons = []
    queued = [
        (trip, q) for trip, q in w._queue.items() if w._loads[trip].mission_id == mid
    ]
    for trip, queue in queued:
        reasons.append(
            {
                "kind": "handling_queue",
                "trip_id": trip,
                "depot": queue["depot"],
                "reason": w._reason(trip, at_s),
            }
        )
    for trip, op in w._active.items():
        if op["kind"] != "supply" and w._loads[trip].mission_id == mid:
            reasons.append(
                {
                    "kind": "handling_active",
                    "trip_id": trip,
                    "planned_end_s": op["end_s"],
                }
            )
    for v, move in w._road.items():
        if move["mission_id"] == mid:
            reasons.append(
                {
                    "kind": (
                        "broken_vehicle"
                        if v in w._broken
                        else (
                            "empty_travel"
                            if move["trip_id"] is None
                            else "loaded_travel"
                        )
                    ),
                    "vehicle_id": v,
                }
            )
    for rid, req in w._requests.items():
        if req["mission_id"] == mid and req["status"] not in ("completed", "cancelled"):
            reasons.append(
                {
                    "kind": "recovery",
                    "request_id": rid,
                    "status": req["status"],
                    "waiting_reason": req.get("waiting_reason"),
                }
            )
    job = w._job(mid)
    if job.status == "waiting" and not reasons:
        if not w.ready(mid):
            reasons.append(
                {
                    "kind": "stock",
                    "deficit": {
                        line.item_id: max(
                            0,
                            (line.minimum if job.urgent else line.requested)
                            - job.reserved.get(line.item_id, 0),
                        )
                        for line in job.mission.lines
                    },
                }
            )
        elif w._pack(mid) is None:
            reasons.append(
                {
                    "kind": "fleet_or_route",
                    "free_vehicles": sum(v not in w._busy for v in w._vehicles),
                }
            )
    return reasons
