"""Read-only integrity gate for the four-table dataset bundle."""

from hashlib import sha256
import json
from math import isclose
from pathlib import Path

from .core import natural
from .dataset import validate_observation
from .imports import _object, _constant
from .rolling import validate_rolling_observation
from .delivery_ledger import validate_delivery_ledger
from .cargo_ledger import validate_cargo_ledger
from .journal import replay_journal
from .provenance import validate_manifest
from .context import validate_context, validate_context_journal

LEGACY_FILES = frozenset(
    (
        "observations.jsonl",
        "labels.jsonl",
        "rolling_observations.jsonl",
        "rolling_targets.jsonl",
        "delivery_events.jsonl",
        "cargo_events.jsonl",
    )
)
FILES = LEGACY_FILES | {"operational_events.jsonl", "planning_contexts.jsonl"}


def validate_label(label, creation):
    fields = {
        "schema_version",
        "simulation_id",
        "mission_id",
        "label_cutoff_s",
        "status",
        "late",
        "delay_minutes",
        "quota_reached_s",
        "quota_censored",
        "logistics_open",
        "eligible",
    }
    if (
        set(label) != fields
        or type(label["schema_version"]) is not int
        or label["schema_version"] != 1
    ):
        raise ValueError("unsupported label contract")
    for field in ("quota_censored", "logistics_open", "eligible"):
        if type(label[field]) is not bool:
            raise ValueError("boolean label flags required")
    if label["late"] is not None and type(label["late"]) is not bool:
        raise ValueError("nullable boolean late required")
    status, quota = label["status"], label["quota_reached_s"]
    start, deadline = (
        creation["features"]["start_s"],
        creation["features"]["deadline_s"],
    )
    cutoff = label["label_cutoff_s"]
    natural(cutoff, "label_cutoff_s")
    if cutoff < start or status not in ("reached", "incomplete", "cancelled"):
        raise ValueError("invalid label status or cutoff")
    if label["eligible"] != (status != "cancelled"):
        raise ValueError("label eligibility inconsistent")
    if label["quota_censored"] != (quota is None and status != "cancelled"):
        raise ValueError("label censoring inconsistent")
    if quota is not None:
        natural(quota, "quota_reached_s")
        if not start <= quota <= cutoff:
            raise ValueError("quota outside observed history")
    if status == "cancelled":
        if label["late"] is not None or label["delay_minutes"] is not None:
            raise ValueError("cancelled mission has timing label")
    elif status == "reached":
        if quota is None or label["late"] is not (quota > deadline):
            raise ValueError("reached label has inconsistent quota or punctuality")
        delay = label["delay_minutes"]
        if type(delay) not in (int, float) or delay != max(0, quota - deadline) / 60:
            raise ValueError("final delay inconsistent with quota")
    elif (
        quota is not None
        or label["delay_minutes"] is not None
        or label["late"] is not (True if cutoff >= deadline else None)
    ):
        raise ValueError("incomplete mission has fabricated timing label")


def _decode(text):
    return json.loads(text, object_pairs_hook=_object, parse_constant=_constant)


def _index(rows, fields):
    indexed = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        if key in indexed:
            raise ValueError("duplicate bundle identity")
        indexed[key] = row
    return indexed


def read_verified_bundle(directory):
    """Reject missing/changed files and broken joins; no writes or partial result.

    Checksums detect changes against the supplied manifest, not authenticity.
    This gate does not replace full semantic validation of external labels.
    """
    root = Path(directory)
    try:
        if (root / "manifest.json").is_symlink():
            raise ValueError("symlink manifest not allowed")
        manifest = _decode((root / "manifest.json").read_text(encoding="utf-8"))
        version = manifest["schema_version"]
        required_files = FILES if version == 4 else LEGACY_FILES
        if (
            type(manifest["schema_version"]) is not int
            or manifest["schema_version"] not in (3, 4)
            or manifest["feature_version"] != "creation-v1"
            or manifest["rolling_feature_version"] != "rolling-v1"
            or set(manifest["files"]) != required_files
        ):
            raise ValueError("unsupported bundle manifest")
        natural(manifest["config"]["seed"], "seed")
        if manifest["group_id"] != f"base-seed-{manifest['config']['seed']}":
            raise ValueError("seed group mismatch")
        tables = {}
        for name in sorted(required_files):
            path = root / name
            if path.is_symlink():
                raise ValueError("symlink data file not allowed")
            data = path.read_bytes()
            description = manifest["files"][name]
            natural(description["rows"], "rows")
            if sha256(data).hexdigest() != description["sha256"]:
                raise ValueError(f"checksum mismatch: {name}")
            rows = [_decode(line) for line in data.decode("utf-8").splitlines()]
            if len(rows) != description["rows"] or any(
                not isinstance(r, dict) for r in rows
            ):
                raise ValueError(f"row count/type mismatch: {name}")
            tables[name] = rows
        validate_bundle_tables(manifest, tables)
        return {"manifest": manifest, "tables": tables}
    except (KeyError, TypeError, AttributeError, OSError, UnicodeError) as error:
        raise ValueError(f"invalid or unreadable bundle: {error}") from error


def validate_bundle_tables(manifest, tables):
    creations = _index(tables["observations.jsonl"], ("simulation_id", "mission_id"))
    labels = _index(tables["labels.jsonl"], ("simulation_id", "mission_id"))
    if creations.keys() != labels.keys():
        raise ValueError("creation/label references mismatch")
    for key, row in creations.items():
        validate_observation(row)
        validate_label(labels[key], row)
        natural(labels[key]["label_cutoff_s"], "label_cutoff_s")
        if row["observed_s"] > labels[key]["label_cutoff_s"]:
            raise ValueError("creation beyond label cutoff")
    rolling = _index(
        tables["rolling_observations.jsonl"], ("simulation_id", "observation_id")
    )
    targets = _index(
        tables["rolling_targets.jsonl"], ("simulation_id", "observation_id")
    )
    if rolling.keys() != targets.keys():
        raise ValueError("rolling/target references mismatch")
    weights = {}
    for key, row in rolling.items():
        target = targets[key]
        mid = (row["simulation_id"], row["mission_id"])
        if mid not in creations or target["mission_id"] != row["mission_id"]:
            raise ValueError("orphan rolling mission")
        validate_rolling_observation(
            row, creations[mid], labels[mid]["label_cutoff_s"], labels[mid]
        )
        if row["feature_version"] != "rolling-v1" or row["schema_version"] != 1:
            raise ValueError("unsupported rolling version")
        natural(row["observed_s"], "observed_s")
        if (
            target["label_cutoff_s"] != labels[mid]["label_cutoff_s"]
            or not creations[mid]["observed_s"]
            <= row["observed_s"]
            <= target["label_cutoff_s"]
        ):
            raise ValueError("rolling cutoff mismatch")
        if (
            type(target["eligible"]) is not bool
            or target["eligible"] != labels[mid]["eligible"]
        ):
            raise ValueError("eligibility mismatch")
        label = labels[mid]
        if (
            target["late"] is not label["late"]
            or type(target["quota_censored"]) is not bool
            or target["quota_censored"] != label["quota_censored"]
        ):
            raise ValueError("rolling label mismatch")
        now = row["observed_s"]
        quota = label["quota_reached_s"]
        if quota is not None and now >= quota:
            raise ValueError("sample after quota completion")
        after = now >= creations[mid]["features"]["deadline_s"]
        kind = "remaining_after_deadline" if after else "delay_if_late"
        expected = (
            ((quota - now) / 60 if after else label["delay_minutes"])
            if (label["eligible"] and quota is not None and label["late"] is True)
            else None
        )
        if target["target_kind"] != kind or target["target_minutes"] != expected:
            raise ValueError("rolling target inconsistent with final label")
        if expected is not None and type(target["target_minutes"]) not in (
            int,
            float,
        ):
            raise ValueError("numeric rolling target required")
        weight = target["sample_weight"]
        if type(weight) not in (int, float) or not 0 <= weight <= 1:
            raise ValueError("invalid sample weight")
        if target["eligible"]:
            weights[mid] = weights.get(mid, 0) + weight
        elif weight != 0:
            raise ValueError("ineligible sample has nonzero weight")
    if any(
        not isclose(weight, 1, rel_tol=1e-12, abs_tol=1e-12)
        for weight in weights.values()
    ):
        raise ValueError("mission weights do not sum to one")
    validate_delivery_ledger(
        tables["delivery_events.jsonl"],
        creations,
        labels,
        tables["rolling_observations.jsonl"],
    )
    validate_cargo_ledger(
        tables["cargo_events.jsonl"],
        tables["delivery_events.jsonl"],
        creations,
        labels,
    )
    if manifest["schema_version"] == 4:
        validate_manifest(manifest["run_manifest"], manifest["config"])
        from datetime import datetime, timedelta

        epoch = datetime.fromisoformat(manifest["run_manifest"]["epoch_utc"])
        events = tables["operational_events.jsonl"]
        if (
            not events
            or events[0]["changes"].get("stock")
            != manifest["run_manifest"]["initial_stock"]
        ):
            raise ValueError("journal initial stock differs from manifest")
        for event in events:
            if (
                event["observed_utc"]
                != (epoch + timedelta(seconds=event["observed_s"])).isoformat()
            ):
                raise ValueError("journal UTC timestamp mismatch")
        cutoff = manifest["label_cutoff_s"]
        natural(cutoff, "label_cutoff_s")
        if any(row["label_cutoff_s"] != cutoff for row in labels.values()):
            raise ValueError("bundle cutoff mismatch")
        if any(
            row["observed_s"] > cutoff for row in tables["operational_events.jsonl"]
        ):
            raise ValueError("journal event beyond bundle cutoff")
        state = replay_journal(
            tables["operational_events.jsonl"],
            manifest["run_manifest"]["simulation_id"],
            cutoff,
        )
        if labels and set(state.get("missions", {})) != {key[1] for key in labels}:
            raise ValueError("journal/mission contract mismatch")
        contexts = _index(
            tables["planning_contexts.jsonl"], ("simulation_id", "observation_id")
        )
        observations = _index(
            tables["observations.jsonl"] + tables["rolling_observations.jsonl"],
            ("simulation_id", "observation_id"),
        )
        if contexts.keys() != observations.keys():
            raise ValueError("missing or orphan planning context")
        for key, row in contexts.items():
            validate_context(row, observations[key])
        validate_context_journal(
            tables["planning_contexts.jsonl"], tables["operational_events.jsonl"]
        )
