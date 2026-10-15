"""Auditable candidate registry; explicit manual approval never bypasses a gate."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def sha256(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def safe_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root):
        raise ValueError("artifact outside repository")
    return path


def empty_registry():
    return {"registry_version": 1, "active": None, "versions": {}, "history": []}


def verify_version(registry, version, root, require_eligible=False):
    entry = registry["versions"][version]
    for name in ("artifact", "evaluation"):
        path = safe_path(root, entry[name]["path"])
        if sha256(path) != entry[name]["sha256"]:
            raise ValueError(name + " checksum mismatch")
    for reference in entry.get("references", {}).values():
        if sha256(safe_path(root, reference["path"])) != reference["sha256"]:
            raise ValueError("reference checksum mismatch")
    evaluation = json.loads(safe_path(root, entry["evaluation"]["path"]).read_text())
    if require_eligible and evaluation["promotion"]["eligible"] is not True:
        raise ValueError("candidate did not pass eligibility gate")
    return entry


def register_candidate(registry, version, entry, root):
    updated = deepcopy(registry)
    if registry["registry_version"] != 1:
        raise ValueError("unsupported registry version")
    if version in updated["versions"]:
        if updated["versions"][version] != entry:
            raise ValueError("version is immutable")
        verify_version(updated, version, root)
        return updated
    updated["versions"][version] = deepcopy(entry)
    verify_version(updated, version, root)
    updated["history"].append(
        {
            "event": "candidate_registered",
            "version": version,
            "at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    return updated


def manual_approval(approval):
    if (
        approval.get("approved") is not True
        or not isinstance(approval.get("approved_by"), str)
        or not approval["approved_by"].strip()
        or not isinstance(approval.get("reason"), str)
        or not approval["reason"].strip()
    ):
        raise ValueError("explicit approver and reason required")


def promote(registry, version, root, approval):
    manual_approval(approval)
    verify_version(registry, version, root, require_eligible=True)
    updated = deepcopy(registry)
    previous = updated["active"]
    updated["active"] = version
    updated["history"].append(
        {
            "event": "promoted",
            "version": version,
            "previous": previous,
            "approval": deepcopy(approval),
            "at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    return updated


def rollback(registry, version, root, approval):
    manual_approval(approval)
    if not any(
        h["event"] == "promoted" and h["version"] == version
        for h in registry["history"]
    ):
        raise ValueError("rollback target was never active")
    verify_version(registry, version, root, require_eligible=True)
    updated = deepcopy(registry)
    previous = updated["active"]
    updated["active"] = version
    updated["history"].append(
        {
            "event": "rollback",
            "version": version,
            "previous": previous,
            "approval": deepcopy(approval),
            "at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    return updated


def active_artifact(registry, root):
    if registry["active"] is None:
        raise ValueError("no manually promoted model")
    entry = verify_version(registry, registry["active"], root, require_eligible=True)
    return safe_path(root, entry["artifact"]["path"])


def write_registry(path, registry):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(registry, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    temporary.replace(path)
