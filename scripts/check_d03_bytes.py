"""Verify persisted checkpoint bytes without loading the large JSON tables."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    value = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def audit(root, output):
    failures = []
    accepted = 0
    for path in sorted((root / "records").glob("*.json")):
        record = json.loads(path.read_text())
        if record.get("valid") is not True:
            continue
        accepted += 1
        bundle = root / record["bundle"]
        manifest_path = bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        expected = {
            "manifest.json": record["manifest_sha256"],
            **{name: info["sha256"] for name, info in manifest["files"].items()},
        }
        paths = [(bundle / name, value) for name, value in expected.items()]
        paths.append((root / record["trace"], record["trace_sha256"]))
        for file, checksum in paths:
            actual = digest(file) if file.is_file() else None
            if actual != checksum:
                failures.append(
                    {
                        "simulation_id": record["simulation_id"],
                        "record": str(path.relative_to(root)),
                        "path": str(file.relative_to(root)),
                        "expected_sha256": checksum,
                        "actual_sha256": actual,
                        "stored_bytes": file.stat().st_size if file.exists() else None,
                    }
                )
    report = {
        "passed": not failures,
        "accepted_records_scanned": accepted,
        "failures": failures,
    }
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)
    return not failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if audit(args.batch, args.output) else 1)
