"""Quarantine JSONL rows, then validate every relation against a verified bundle."""

from copy import deepcopy
import json

from .bundles import validate_bundle_tables
from .imports import _object, _constant


def import_table(text, table_name, verified_bundle):
    if table_name not in verified_bundle["tables"]:
        raise ValueError("unknown table contract")
    rows, quarantine, seen = [], [], {}
    critical = []
    source = text.splitlines()
    for number, raw in enumerate(source, 1):
        try:
            row = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant)
            if (
                not isinstance(row, dict)
                or type(row.get("schema_version")) is not int
                or row["schema_version"] != 1
            ):
                raise ValueError("row requires versioned object contract")
        except (ValueError, TypeError) as error:
            quarantine.append({"line": number, "raw": raw, "reason": str(error)})
            continue
        fields = (
            ("simulation_id", "observation_id")
            if "observation_id" in row
            else (
                ("simulation_id", "event_id")
                if "event_id" in row
                else (
                    ("simulation_id", "mission_id", "kind", "at_s", "cargo")
                    if table_name == "cargo_events.jsonl"
                    else ("simulation_id", "mission_id")
                )
            )
        )
        try:
            identity = json.dumps([row[f] for f in fields], sort_keys=True)
        except KeyError as error:
            quarantine.append({"line": number, "raw": raw, "reason": str(error)})
            continue
        if identity in seen:
            if seen[identity] != row:
                critical.append({"line": number, "reason": "conflicting row identity"})
            continue
        seen[identity] = row
        rows.append(row)
    excessive = len(quarantine) * 200 > len(source)
    candidate = deepcopy(verified_bundle["tables"])
    candidate[table_name] = rows
    if not excessive and not critical:
        try:
            validate_bundle_tables(verified_bundle["manifest"], candidate)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            critical.append({"reason": str(error)})
    blocked = excessive or bool(critical)
    return {
        "blocked": blocked,
        "records": [] if blocked else rows,
        "quarantine": quarantine,
        "critical": critical,
        "total_rows": len(source),
        "invalid_rows": len(quarantine),
        "threshold_exceeded": excessive,
    }
