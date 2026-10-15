"""Create a deterministic source/demo ZIP with an explicit checksum manifest."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ("src", "conf", "scripts", "docs", "tests", "models", "examples")
REPORTS = ("m01-v1", "m02-v1", "m03-v1", "u01-v1")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_files(root):
    result, excluded = [], []
    candidates = [p for directory in DIRECTORIES for p in (root / directory).rglob("*")]
    candidates += [
        p for folder in REPORTS for p in (root / "reports" / folder).rglob("*")
    ]
    candidates += [
        root / "reports/d03-batch-v1" / name
        for name in ("plan.json", "split_manifest.json")
    ]
    candidates += [
        root / "data/d03" / name for name in ("README.md", "Verifica_Dataset_D03.json")
    ]
    candidates += list(root.glob("requirements*.txt")) + list(
        root.glob("requirements*.in")
    )
    candidates += [
        root / name
        for name in ("README.md", "pyproject.toml", "conftest.py", "pytest.ini")
    ]
    for p in sorted(set(candidates)):
        relative = p.relative_to(root)
        if not p.is_file() or any(
            part.startswith(".") or part == "__pycache__" for part in relative.parts
        ):
            continue
        if p.is_symlink():
            raise ValueError("symlinks are not package inputs")
        if p.suffix in (".pyc", ".pyo"):
            continue
        if p.name.endswith((".jsonl.gz", ".jsonl", ".zip", ".part01", ".part02")):
            excluded.append(
                {
                    "path": relative.as_posix(),
                    "reason": "separate historical dataset/inference payload",
                }
            )
            continue
        if p.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("unexpected large input: " + str(relative))
        result.append(relative.as_posix())
    return result, excluded


def build(root, output, base_commit=None):
    files, excluded = package_files(root)
    if not files or "requirements-local.txt" not in files:
        raise ValueError("resolved local lock is required")
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unavailable"
    if base_commit is not None:
        if len(base_commit) != 40 or any(
            c not in "0123456789abcdef" for c in base_commit
        ):
            raise ValueError("base commit must be a full lowercase SHA")
        revision = base_commit
    manifest = {
        "package_version": "r01-v1",
        "python": "3.12",
        "base_commit": revision,
        "source_identity": (
            "sha256 of packaged files; " "base commit may precede release changes"
        ),
        "sha256": {p: digest(root / p) for p in files},
        "excluded_payloads": excluded,
        "dataset": "https://github.com/Zistax/digital-twin-military-logistics/tree/d03-dataset-v1",
        "model_status": "experimental candidates; no model promoted",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in files + ["PACKAGE-MANIFEST.json"]:
            info = zipfile.ZipInfo(
                "digital-twin-local/" + name, date_time=(2026, 10, 15, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            data = (
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
                if name == "PACKAGE-MANIFEST.json"
                else (root / name).read_bytes()
            )
            archive.writestr(info, data)
    return {
        "path": output.name,
        "sha256": digest(output),
        "bytes": output.stat().st_size,
        "files": len(files),
        "manifest": manifest,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--base-commit", help="manifest base for byte-identical rebuilds"
    )
    args = parser.parse_args()
    result = build(ROOT, args.output.resolve(), args.base_commit)
    args.output.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "manifest"}))


if __name__ == "__main__":
    main()
