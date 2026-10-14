"""Versioned creation observations, separate final labels and reproducible exports."""

from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

from .core import natural, identifier

FEATURE_FIELDS = frozenset(
    (
        "origin_id",
        "destination_id",
        "urgent",
        "start_s",
        "deadline_s",
        "deadline_source",
        "estimated_duration_s",
        "estimate_unavailable_reason",
        "free_vehicles",
        "lines",
    )
)
LINE_FIELDS = frozenset(
    (
        "item_id",
        "requested",
        "minimum",
        "kg",
        "m3",
        "cold",
        "available_origin",
        "stock_destination",
    )
)


def creation_observation(w, request, mission, estimate, deadline_source):
    """Capture now; never reconstruct creation features from final snapshots."""
    at_s = request.start_s
    if w._clock != at_s or estimate.observed_s != at_s:
        raise ValueError("observation must be captured at creation")
    features = {
        "origin_id": mission.origin_id,
        "destination_id": mission.destination_id,
        "urgent": request.urgent,
        "start_s": at_s,
        "deadline_s": mission.deadline_s,
        "deadline_source": deadline_source,
        "estimated_duration_s": estimate.duration_s,
        "estimate_unavailable_reason": estimate.reason,
        "free_vehicles": sum(
            v not in w._busy and v not in w._broken and w._positions[v] is not None
            for v in w._vehicles
        ),
        "lines": [
            {
                "item_id": line.item_id,
                "requested": line.requested,
                "minimum": line.minimum,
                "kg": str(w._items[line.item_id].kg),
                "m3": str(w._items[line.item_id].m3),
                "cold": w._items[line.item_id].cold,
                "available_origin": w.available(mission.origin_id, line.item_id),
                "stock_destination": w._stock[mission.destination_id].get(
                    line.item_id, 0
                ),
            }
            for line in mission.lines
        ],
    }
    return {
        "schema_version": 1,
        "feature_version": "creation-v1",
        "simulation_id": w.simulation_id,
        "mission_id": mission.mission_id,
        "observation_id": f"{mission .mission_id }:creation",
        "observed_s": at_s,
        "observed_utc": (w._epoch + timedelta(seconds=at_s)).isoformat(),
        "features": features,
    }


def validate_observation(record):
    expected = {
        "schema_version",
        "feature_version",
        "simulation_id",
        "mission_id",
        "observation_id",
        "observed_s",
        "observed_utc",
        "features",
    }
    if (
        set(record) != expected
        or record["schema_version"] != 1
        or record["feature_version"] != "creation-v1"
    ):
        raise ValueError("unsupported observation contract")
    features = record["features"]
    if type(record["schema_version"]) is not int:
        raise ValueError("integer schema version required")
    for field in ("simulation_id", "mission_id", "observation_id"):
        identifier(record[field])
    instant = datetime.fromisoformat(record["observed_utc"])
    if instant.utcoffset() != timedelta(0):
        raise ValueError("UTC observation timestamp required")
    if set(features) != FEATURE_FIELDS:
        raise ValueError("unapproved feature: possible future leakage")
    natural(record["observed_s"], "observed_s")
    natural(features["start_s"], "start_s")
    natural(features["deadline_s"], "deadline_s")
    natural(features["free_vehicles"], "free_vehicles")
    if (
        features["deadline_s"] <= features["start_s"]
        or type(features["urgent"]) is not bool
    ):
        raise ValueError("invalid mission features")
    for field in ("origin_id", "destination_id"):
        identifier(features[field])
    if features["origin_id"] == features["destination_id"]:
        raise ValueError("distinct depots required")
    if features["deadline_source"] not in (
        "observable_estimate",
        "configured_allowance",
    ):
        raise ValueError("unknown deadline source")
    if features["estimated_duration_s"] is not None:
        natural(features["estimated_duration_s"], "estimated_duration_s", True)
        if features["estimate_unavailable_reason"] is not None:
            raise ValueError("finite estimate cannot have unavailable reason")
    elif not isinstance(features["estimate_unavailable_reason"], str):
        raise ValueError("unavailable estimate requires reason")
    if record["observed_s"] != features["start_s"]:
        raise ValueError("creation feature cutoff mismatch")
    if not features["lines"]:
        raise ValueError("empty mission lines")
    items = set()
    for line in features["lines"]:
        if set(line) != LINE_FIELDS or line["item_id"] in items:
            raise ValueError("invalid or duplicate line")
        items.add(line["item_id"])
        identifier(line["item_id"])
        if type(line["cold"]) is not bool:
            raise ValueError("boolean cold flag required")
        for field in ("kg", "m3"):
            value = Decimal(line[field])
            if not value.is_finite() or value <= 0:
                raise ValueError("positive finite measure required")
        for field in ("requested", "minimum", "available_origin", "stock_destination"):
            natural(line[field], field, field in ("requested", "minimum"))
        if line["minimum"] > line["requested"]:
            raise ValueError("minimum exceeds requested")


def build_creation_dataset(result):
    """Strict internal export: any invalid relation blocks the entire dataset."""
    observations = []
    seen = {}
    for observation in result["observations"]:
        validate_observation(observation)
        key = (observation["simulation_id"], observation["observation_id"])
        if key in seen:
            if seen[key] != observation:
                raise ValueError("conflicting duplicate observation")
            continue
        seen[key] = observation
        if observation["observed_s"] > result["stopped_s"]:
            raise ValueError("observation after run cutoff")
        observations.append(deepcopy(observation))
    if len({o["simulation_id"] for o in observations}) > 1:
        raise ValueError("single simulation required")
    if {o["mission_id"] for o in observations} != set(result["outcomes"]):
        raise ValueError("orphan observation or outcome")
    if len({o["mission_id"] for o in observations}) != len(observations):
        raise ValueError("multiple creation observations for mission")
    labels = []
    for observation in observations:
        mid = observation["mission_id"]
        outcome = result["outcomes"][mid]
        quota = outcome["quota_reached_s"]
        if quota is not None:
            natural(quota, "quota_reached_s")
            if not observation["observed_s"] <= quota <= result["stopped_s"]:
                raise ValueError("quota time outside mission history")
            if outcome["status"] != "cancelled":
                deadline = observation["features"]["deadline_s"]
                if (
                    outcome["late"] is not (quota > deadline)
                    or outcome["delay_minutes"] != max(0, quota - deadline) / 60
                ):
                    raise ValueError("final timing label inconsistent with quota")
        if outcome["quota_censored"] != (
            quota is None and outcome["status"] != "cancelled"
        ):
            raise ValueError("inconsistent censoring flag")
        labels.append(
            {
                "schema_version": 1,
                "simulation_id": observation["simulation_id"],
                "mission_id": mid,
                "label_cutoff_s": result["stopped_s"],
                "status": outcome["status"],
                "late": outcome["late"],
                "delay_minutes": outcome["delay_minutes"],
                "quota_reached_s": outcome["quota_reached_s"],
                "quota_censored": outcome["quota_censored"],
                "logistics_open": outcome["logistics_open"],
                "eligible": outcome["status"] != "cancelled",
            }
        )
        if outcome["quota_reached_s"] is None and outcome["delay_minutes"] is not None:
            raise ValueError("incomplete outcome has fabricated final delay")
    eligible = [entry for entry in labels if entry["eligible"]]
    reached = [entry for entry in eligible if entry["quota_reached_s"] is not None]
    kpi = {
        "missions": len(labels),
        "cancelled": len(labels) - len(eligible),
        "quota_reached": len(reached),
        "quota_censored": sum(entry["quota_censored"] for entry in eligible),
        "known_late": sum(entry["late"] is True for entry in eligible),
        "timing_unknown": sum(entry["late"] is None for entry in eligible),
        "on_time_reached": sum(entry["late"] is False for entry in reached),
        "mean_delay_reached_minutes": (
            sum(entry["delay_minutes"] for entry in reached) / len(reached)
            if reached
            else None
        ),
    }
    return {
        "observations": observations,
        "labels": labels,
        "kpi": kpi,
        "group_id": f"base-seed-{result ['config']['seed']}",
        "config": deepcopy(result["config"]),
    }


def export_creation_dataset(result, directory):
    """Write a new bundle; refusing existing directories prevents silent replacement."""
    dataset = build_creation_dataset(result)
    from .rolling import build_rolling_dataset

    rolling = build_rolling_dataset(result)
    files = {
        "observations.jsonl": dataset["observations"],
        "labels.jsonl": dataset["labels"],
    }
    files.update(
        {
            "rolling_observations.jsonl": rolling["observations"],
            "rolling_targets.jsonl": rolling["targets"],
        }
    )
    from .delivery_ledger import validate_delivery_ledger

    events = result["delivery_events"]
    validate_delivery_ledger(
        events,
        {(r["simulation_id"], r["mission_id"]): r for r in dataset["observations"]},
        {(r["simulation_id"], r["mission_id"]): r for r in dataset["labels"]},
        rolling["observations"],
    )
    files["delivery_events.jsonl"] = events
    from .cargo_ledger import validate_cargo_ledger

    cargo = result["cargo_events"]
    validate_cargo_ledger(
        cargo,
        events,
        {(r["simulation_id"], r["mission_id"]): r for r in dataset["observations"]},
        {(r["simulation_id"], r["mission_id"]): r for r in dataset["labels"]},
    )
    files["cargo_events.jsonl"] = cargo
    from .journal import replay_journal
    from .provenance import validate_manifest

    validate_manifest(result["run_manifest"], result["config"])
    replay_journal(
        result["operational_events"],
        result["run_manifest"]["simulation_id"],
        result["stopped_s"],
    )
    files["operational_events.jsonl"] = result["operational_events"]
    from .context import validate_context, validate_context_journal

    obs_index = {
        (row["simulation_id"], row["observation_id"]): row
        for row in dataset["observations"] + rolling["observations"]
    }
    for row in result["planning_contexts"]:
        validate_context(row, obs_index[(row["simulation_id"], row["observation_id"])])
    validate_context_journal(result["planning_contexts"], result["operational_events"])
    files["planning_contexts.jsonl"] = result["planning_contexts"]
    encoded = {
        name: "".join(
            json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows
        )
        for name, rows in files.items()
    }
    manifest = {
        "schema_version": 4,
        "label_cutoff_s": result["stopped_s"],
        "run_manifest": result["run_manifest"],
        "feature_version": "creation-v1",
        "rolling_feature_version": "rolling-v1",
        "config": dataset["config"],
        "group_id": dataset["group_id"],
        "kpi": dataset["kpi"],
        "files": {
            name: {
                "rows": len(files[name]),
                "sha256": sha256(body.encode()).hexdigest(),
            }
            for name, body in encoded.items()
        },
    }
    encoded["manifest.json"] = (
        json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + "\n"
    )
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    for name, body in encoded.items():
        (directory / name).write_bytes(body.encode("utf-8"))
    return manifest
