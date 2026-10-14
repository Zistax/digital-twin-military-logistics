"""Cross-check inspected quantities and quota times against a delivery ledger."""

from dataclasses import fields
from datetime import datetime, timedelta

from .core import Delivery


def validate_delivery_ledger(events, creations, labels, rolling):
    event_fields = {f.name for f in fields(Delivery)}
    seen, grouped = set(), {key: [] for key in creations}
    for row in events:
        if set(row) != event_fields | {"occurred_utc", "observed_utc"}:
            raise ValueError("invalid delivery event contract")
        event = Delivery(**{name: row[name] for name in event_fields})
        identity = (event.simulation_id, event.event_id)
        if identity in seen:
            raise ValueError("duplicate delivery event")
        seen.add(identity)
        key = (event.simulation_id, event.mission_id)
        if key not in creations:
            raise ValueError("orphan delivery event")
        creation, label = creations[key], labels[key]
        if (
            event.item_id
            not in {entry["item_id"] for entry in creation["features"]["lines"]}
            or not creation["observed_s"]
            <= event.occurred_s
            <= event.observed_s
            <= label["label_cutoff_s"]
        ):
            raise ValueError("delivery item or time outside mission contract")
        epoch = datetime.fromisoformat(creation["observed_utc"]) - timedelta(
            seconds=creation["observed_s"]
        )
        for clock in ("occurred", "observed"):
            if (
                row[clock + "_utc"]
                != (epoch + timedelta(seconds=row[clock + "_s"])).isoformat()
            ):
                raise ValueError("delivery UTC mismatch")
        grouped[key].append(event)
    for key, creation in creations.items():
        minima = {
            line["item_id"]: line["minimum"] for line in creation["features"]["lines"]
        }
        accepted = dict.fromkeys(minima, 0)
        quota = None
        for event in sorted(grouped[key], key=lambda e: (e.observed_s, e.event_id)):
            accepted[event.item_id] += event.accepted
            if quota is None and all(accepted[i] >= q for i, q in minima.items()):
                quota = event.observed_s
        if quota != labels[key]["quota_reached_s"]:
            raise ValueError("quota time unsupported by delivery ledger")
    for row in rolling:
        key = (row["simulation_id"], row["mission_id"])
        if key not in grouped:
            raise ValueError("orphan rolling mission")
        accepted, unusable = {}, {}
        for event in grouped[key]:
            if event.observed_s <= row["observed_s"]:
                accepted[event.item_id] = (
                    accepted.get(event.item_id, 0) + event.accepted
                )
                unusable[event.item_id] = (
                    unusable.get(event.item_id, 0) + event.unusable
                )
        for line in row["features"]["lines"]:
            if line["accepted"] != accepted.get(line["item_id"], 0) or line[
                "unusable_inspected"
            ] != unusable.get(line["item_id"], 0):
                raise ValueError(
                    "rolling quantity unsupported by observed delivery events"
                )
