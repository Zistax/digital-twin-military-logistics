"""Package the offline R02 demo without credentials, databases or bulk datasets."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_local_package import package_files  # noqa: E402


def build(root, output, include_container_report=False, include_load_report=False):
    if include_load_report:
        include_container_report = True
        load = json.loads((root / "reports/r02-load-v1/verification.json").read_text())
        if load.get("passed") is not True:
            raise ValueError("passing load report required")
        observed = load.get("validated_runtime_sha256", {})
        if not observed:
            raise ValueError("load runtime checksums required")
        for name, expected in observed.items():
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError("unsafe load evidence path")
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("load evidence is stale: " + name)
    files, excluded = package_files(root)
    files += [
        "LICENSE",
        ".gitignore",
        ".dockerignore",
        "reports/r01-v1/pilot-summary.json",
    ]
    files += [
        "reports/r02-v1/Chiusura_R02.md",
        "reports/r02-v1/verification.json",
        "reports/r02-v1/http-extracted.json",
        "reports/r02-v1/boundaries.xml",
        "reports/quality-r02-final-20261015/quality.json",
    ]
    files += [
        p.relative_to(root).as_posix()
        for p in (root / "deploy").rglob("*")
        if p.is_file()
    ]
    files = sorted(set(files))
    if include_container_report:
        evidence_path = (
            "reports/r02-load-v1/container-verification.json"
            if include_load_report
            else "reports/r02-container-v1/verification.json"
        )
        report = json.loads((root / evidence_path).read_text())
        if report.get("passed") is not True:
            raise ValueError("passing container report required")
        evidence = report.get("validated_source_sha256", {})
        if not evidence:
            raise ValueError("container source checksums required")
        for name, expected in evidence.items():
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError("unsafe evidence path")
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("container evidence is stale: " + name)
        files += [
            "reports/r02-container-v1/verification.json",
            "reports/r02-container-v1/Chiusura_Container.md",
            "reports/r02-container-v1/package-tests.xml",
        ]
        if include_load_report:
            files += [
                "reports/r02-load-v1/verification.json",
                "reports/r02-load-v1/container-verification.json",
                "reports/r02-load-v1/Chiusura_Load.md",
                "reports/r02-load-v1/admission-before.json",
                "reports/r02-load-v1/revocation-before.xml",
                "reports/r02-load-v1/package-tests.xml",
                "reports/quality-r02-load-final-20261015/quality.json",
            ]
        files = sorted(set(files))
    if not files or "src/api/demo_app.py" not in files:
        raise ValueError("R02 source missing")
    checksums = {}
    for name in files:
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("unsafe package path")
        checksums[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "package": (
            "r02-load-v1"
            if include_load_report
            else "r02-container-v1" if include_container_report else "r02-offline-v1"
        ),
        "python": "3.12",
        "sha256": checksums,
        "excluded_payloads": excluded,
        "public_deployment_verified": False,
        "runtime_secrets_included": False,
        "active_model": None,
        "container_verified": include_container_report,
        "load_verified": include_load_report,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in files + ["DEMO-MANIFEST.json"]:
            info = zipfile.ZipInfo("digital-twin-demo/" + name, (2026, 10, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            data = (
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
                if name == "DEMO-MANIFEST.json"
                else (root / name).read_bytes()
            )
            archive.writestr(info, data)
    result = {
        "file": output.name,
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "files": len(files),
        "public_deployment_verified": False,
        "container_verified": include_container_report,
        "load_verified": include_load_report,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-container-report", action="store_true")
    parser.add_argument("--include-load-report", action="store_true")
    args = parser.parse_args()
    result = build(
        ROOT,
        args.output.resolve(),
        args.include_container_report,
        args.include_load_report,
    )
    args.output.with_suffix(".json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
