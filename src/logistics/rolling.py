"""Live rolling observations: inspected deliveries only, never retrospective
snapshots."""

from datetime import timedelta
from datetime import datetime
from copy import deepcopy
from collections import Counter

from .core import natural, identifier


def rolling_observations(w):
    now = w._clock
    records = []
    for mid, job in sorted(w._jobs.items()):
        mission = job.mission
        if mission.start_s > now or mid in w._cancelled:
            continue
        accepted = {line.item_id: 0 for line in mission.lines}
        unusable = dict.fromkeys(accepted, 0)
        for event in w._events:
            if event.mission_id == mid and event.observed_s <= now:
                accepted[event.item_id] += event.accepted
                unusable[event.item_id] += event.unusable
        if all(accepted[line.item_id] >= line.minimum for line in mission.lines):
            continue
        records.append(
            {
                "schema_version": 1,
                "feature_version": "rolling-v1",
                "simulation_id": w.simulation_id,
                "mission_id": mid,
                "observation_id": f"{mid }:rolling:{now }",
                "observed_s": now,
                "observed_utc": (w._epoch + timedelta(seconds=now)).isoformat(),
                "features": {
                    "status": job.status,
                    "elapsed_s": now - mission.start_s,
                    "seconds_to_deadline": mission.deadline_s - now,
                    "urgent": job.urgent,
                    "lines": [
                        {
                            "item_id": line.item_id,
                            "minimum": line.minimum,
                            "accepted": accepted[line.item_id],
                            "unusable_inspected": unusable[line.item_id],
                            "reserved": job.reserved.get(line.item_id, 0),
                        }
                        for line in mission.lines
                    ],
                    "recovery_statuses": [
                        r["status"]
                        for _, r in sorted(w._requests.items())
                        if r["mission_id"] == mid and r["created_s"] <= now
                    ],
                },
            }
        )
    return records


def validate_rolling_observation(row, original, cutoff_s, outcome):
    record_fields = {
        "schema_version",
        "feature_version",
        "simulation_id",
        "mission_id",
        "observation_id",
        "observed_s",
        "observed_utc",
        "features",
    }
    feature_fields = {
        "status",
        "elapsed_s",
        "seconds_to_deadline",
        "urgent",
        "lines",
        "recovery_statuses",
    }
    line_fields = {"item_id", "minimum", "accepted", "unusable_inspected", "reserved"}
    if (
        set(row) != record_fields
        or type(row["schema_version"]) is not int
        or row["schema_version"] != 1
        or row["feature_version"] != "rolling-v1"
    ):
        raise ValueError("unsupported rolling contract")
    if (row["simulation_id"], row["mission_id"]) != (
        original["simulation_id"],
        original["mission_id"],
    ):
        raise ValueError("orphan rolling observation")
    natural(row["observed_s"], "observed_s")
    now = row["observed_s"]
    contract = original["features"]
    features = row["features"]
    if set(features) != feature_fields:
        raise ValueError("unapproved rolling feature")
    if not original["observed_s"] <= now <= cutoff_s:
        raise ValueError("rolling observation outside time bounds")
    expected_utc = datetime.fromisoformat(original["observed_utc"]) + timedelta(
        seconds=now - original["observed_s"]
    )
    if row["observed_utc"] != expected_utc.isoformat():
        raise ValueError("rolling UTC mismatch")
    if (
        type(features["elapsed_s"]) is not int
        or type(features["seconds_to_deadline"]) is not int
        or features["elapsed_s"] != now - contract["start_s"]
        or features["seconds_to_deadline"] != contract["deadline_s"] - now
        or type(features["urgent"]) is not bool
        or features["urgent"] != contract["urgent"]
    ):
        raise ValueError("rolling mission contract mismatch")
    identifier(features["status"])
    if not isinstance(features["recovery_statuses"], list) or any(
        s
        not in (
            "pending",
            "approved",
            "deferred",
            "rejected",
            "in_progress",
            "completed",
            "cancelled",
        )
        for s in features["recovery_statuses"]
    ):
        raise ValueError("unknown recovery status")
    lines = {line["item_id"]: line for line in contract["lines"]}
    observed_items = set()
    for line in features["lines"]:
        if (
            set(line) != line_fields
            or line["item_id"] not in lines
            or line["item_id"] in observed_items
        ):
            raise ValueError("invalid rolling item contract")
        item = line["item_id"]
        observed_items.add(item)
        for field in line_fields - {"item_id"}:
            natural(line[field], field)
        if (
            line["minimum"] != lines[item]["minimum"]
            or ("accepted" in outcome and line["accepted"] > outcome["accepted"][item])
            or (
                "unusable" in outcome
                and line["unusable_inspected"] > outcome["unusable"][item]
            )
        ):
            raise ValueError("rolling quantity inconsistency")
    if observed_items != set(lines) or all(
        entry["accepted"] >= entry["minimum"] for entry in features["lines"]
    ):
        raise ValueError("missing item or already reached quota")
    quota = outcome["quota_reached_s"]
    if quota is not None and now >= quota:
        raise ValueError("rolling observation after quota completion")
    if row["observation_id"] != f"{row ['mission_id']}:rolling:{now }":
        raise ValueError("rolling observation identity mismatch")


def build_rolling_dataset(result):
    """Validate against creation contracts and keep targets outside feature records."""
    from .dataset import build_creation_dataset

    base = build_creation_dataset(result)
    creations = {(r["simulation_id"], r["mission_id"]): r for r in base["observations"]}
    observations, seen = [], {}
    for row in result.get("rolling_observations", []):
        key = (row["simulation_id"], row["mission_id"])
        if key not in creations:
            raise ValueError("orphan rolling observation")
        validate_rolling_observation(
            row,
            creations[key],
            result["stopped_s"],
            result["outcomes"][row["mission_id"]],
        )
        observation_key = (row["simulation_id"], row["observation_id"])
        if observation_key in seen:
            if seen[observation_key] != row:
                raise ValueError("conflicting rolling duplicate")
            continue
        seen[observation_key] = row
        observations.append(deepcopy(row))
    counts = Counter((r["simulation_id"], r["mission_id"]) for r in observations)
    targets = []
    for row in observations:
        mid, now = row["mission_id"], row["observed_s"]
        outcome = result["outcomes"][mid]
        after_deadline = row["features"]["seconds_to_deadline"] <= 0
        quota = outcome["quota_reached_s"]
        eligible = outcome["status"] != "cancelled"
        target = (
            ((quota - now) / 60 if after_deadline else outcome["delay_minutes"])
            if (eligible and quota is not None and outcome["late"] is True)
            else None
        )
        targets.append(
            {
                "schema_version": 1,
                "simulation_id": row["simulation_id"],
                "mission_id": mid,
                "observation_id": row["observation_id"],
                "label_cutoff_s": result["stopped_s"],
                "late": outcome["late"],
                "target_kind": (
                    "remaining_after_deadline" if after_deadline else "delay_if_late"
                ),
                "target_minutes": target,
                "quota_censored": outcome["quota_censored"],
                "eligible": eligible,
                "sample_weight": (
                    1 / counts[(row["simulation_id"], mid)] if eligible else 0
                ),
            }
        )
    return {
        "observations": observations,
        "targets": targets,
        "group_id": base["group_id"],
    }
