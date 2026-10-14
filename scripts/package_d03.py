"""Incrementally package accepted D03 bundles; finalize after the 90-run audit."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


def read_json(path):
    return json.loads(path.read_text())


def file_digest(path):
    result = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def package(root, archive, closeout=None):
    root = root.resolve()
    archive = archive.resolve()
    archive.parent.mkdir(parents=True, exist_ok=True)
    plan = read_json(root / "plan.json")
    desired = {}

    def add(path, expected=None):
        path = path.resolve()
        name = str(path.relative_to(root.parent))
        desired[name] = (path, expected or file_digest(path))

    for name in (
        "plan.json",
        "readiness.json",
        "memory-executor.json",
        "memory-executor-native-equivalence.json",
    ):
        add(root / name)
    records = []
    identities = set()
    for path in sorted((root / "records").glob("*.json")):
        record = read_json(path)
        if record.get("valid") is not True:
            continue
        if (
            record["simulation_id"] in identities
            or record["plan_sha256"] != plan["plan_sha256"]
        ):
            raise ValueError("duplicate identity or changed plan")
        identities.add(record["simulation_id"])
        records.append(record)
        bundle = root / record["bundle"]
        manifest_path = bundle / "manifest.json"
        if file_digest(manifest_path) != record["manifest_sha256"]:
            raise ValueError("changed accepted manifest")
        manifest = read_json(manifest_path)
        add(manifest_path, record["manifest_sha256"])
        for name, info in manifest["files"].items():
            add(bundle / name, info["sha256"])
        add(root / record["trace"], record["trace_sha256"])
        add(path)
    if closeout is not None:
        acceptance = read_json(root / "acceptance.json")
        if (
            acceptance.get("passed") is not True
            or acceptance["verified_runs"] != 90
            or len(records) != 90
        ):
            raise ValueError("cannot finalize an incomplete dataset")
        for name in ("acceptance.json", "split_manifest.json"):
            add(root / name)
        for path in sorted(root.glob("execution-*.json")):
            add(path)
        for path in sorted(root.glob("memory-executor-*-policy.json")):
            add(path)
        add(root / "invalid-attempts-archive.json")
        for path in sorted((root / "storage-repairs").glob("*/restoration.json")):
            add(path)
        for path in sorted(root.glob("storage-audit-*.json")):
            add(path)
        for path in sorted(closeout.resolve().iterdir()):
            if path.is_file():
                add(path)
    count = 0
    with zipfile.ZipFile(
        archive, "a", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True
    ) as output:
        names = output.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate archive members")
        known = set(names)
        if not known <= set(desired):
            raise ValueError("archive contains unexpected entries")
        for name, (path, expected) in desired.items():
            if name in known:
                continue
            result = sha256()
            with (
                path.open("rb") as source,
                output.open(name, "w", force_zip64=True) as target,
            ):
                while chunk := source.read(1024 * 1024):
                    result.update(chunk)
                    target.write(chunk)
            if result.hexdigest() != expected:
                raise ValueError(f"changed source during packaging: {name}")
            count += 1
    print(
        json.dumps(
            {
                "accepted_runs_packaged": len(records),
                "new_entries": count,
                "archive_bytes": archive.stat().st_size,
            }
        ),
        flush=True,
    )
    if closeout is not None:
        with zipfile.ZipFile(archive) as source:
            for name, (_, expected) in desired.items():
                result = sha256()
                with source.open(name) as handle:
                    while chunk := handle.read(1024 * 1024):
                        result.update(chunk)
                if result.hexdigest() != expected:
                    raise ValueError(f"archive SHA256 mismatch: {name}")
        evidence = {
            "passed": True,
            "accepted_runs": 90,
            "verified_entries": len(desired),
            "archive_sha256": file_digest(archive),
            "archive_bytes": archive.stat().st_size,
            "plan_sha256": plan["plan_sha256"],
        }
        archive.with_suffix(archive.suffix + ".verification.json").write_text(
            json.dumps(evidence, indent=2)
        )
        print(json.dumps(evidence), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--closeout", type=Path)
    args = parser.parse_args()
    package(args.batch, args.archive, args.closeout)
