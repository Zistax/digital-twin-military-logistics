"""Strict JSONL observation import with quarantine and exact 0.5% gate."""

from copy import deepcopy
from datetime import timedelta
from decimal import InvalidOperation
import json

from .dataset import FEATURE_FIELDS, LINE_FIELDS, validate_observation
from .core import natural


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("nonfinite JSON constant")


def import_observations(text, *, missions, epoch, cutoff_s):
    """missions maps (simulation_id, mission_id) to authoritative start/deadline.

    Returns no accepted records if any critical violation or >0.5% malformed
    rows exists. Exact duplicate rows are idempotent, but still counted in the
    source row total. UTC timestamps are checked against the supplied run epoch.
    """
    natural(cutoff_s, "cutoff_s")
    if epoch.utcoffset() != timedelta(0):
        raise ValueError("UTC epoch required")
    rows = text.splitlines()
    quarantine, critical, accepted = [], [], []
    seen, mission_seen = {}, {}
    duplicates = 0
    for number, raw in enumerate(rows, 1):
        try:
            record = json.loads(
                raw, object_pairs_hook=_object, parse_constant=_constant
            )
            if not isinstance(record, dict):
                raise ValueError("record must be an object")
            features = record.get("features")
            if isinstance(features, dict):
                observed = record.get("observed_s")
                if type(observed) is int and (
                    observed > cutoff_s or observed != features.get("start_s")
                ):
                    critical.append(
                        {
                            "line": number,
                            "reason": "creation observation cutoff mismatch",
                        }
                    )
                if set(features) - FEATURE_FIELDS:
                    critical.append({"line": number, "reason": "unapproved feature"})
                lines = features.get("lines", [])
                if isinstance(lines, list) and any(
                    isinstance(line, dict) and set(line) - LINE_FIELDS for line in lines
                ):
                    critical.append(
                        {"line": number, "reason": "unapproved line feature"}
                    )
            validate_observation(record)
        except (
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            InvalidOperation,
            OverflowError,
        ) as error:
            quarantine.append({"line": number, "raw": raw, "reason": str(error)})
            continue
        mission_key = (record["simulation_id"], record["mission_id"])
        contract = missions.get(mission_key)
        reason = None
        if contract is None:
            reason = "orphan mission"
        elif (
            features["start_s"] != contract["start_s"]
            or features["deadline_s"] != contract["deadline_s"]
        ):
            reason = "mission contract mismatch"
        elif record["observed_s"] > cutoff_s:
            reason = "observation beyond cutoff"
        elif (
            record["observed_utc"]
            != (epoch + timedelta(seconds=record["observed_s"])).isoformat()
        ):
            reason = "UTC and simulated time mismatch"
        key = (record["simulation_id"], record["observation_id"])
        if key in seen:
            if seen[key] != record:
                reason = "conflicting observation duplicate"
            else:
                duplicates += 1
        elif mission_key in mission_seen:
            reason = "multiple creation observations for mission"
        if reason:
            critical.append({"line": number, "reason": reason})
        elif key not in seen:
            accepted.append(deepcopy(record))
            mission_seen[mission_key] = key
        seen[key] = record
    excessive = len(quarantine) * 200 > len(rows)
    blocked = excessive or bool(critical)
    return {
        "schema_version": 1,
        "blocked": blocked,
        "records": [] if blocked else accepted,
        "quarantine": quarantine,
        "critical": critical,
        "total_rows": len(rows),
        "invalid_rows": len(quarantine),
        "exact_duplicates": duplicates,
        "threshold_exceeded": excessive,
    }
