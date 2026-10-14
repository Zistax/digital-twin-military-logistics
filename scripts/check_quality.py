"""Run real quality gates in isolation, preserving repository runtime data."""

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = {
        "python": sys.version,
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("pytest", "coverage", "black", "ruff")
        },
        "checks": [],
    }
    args.report.mkdir(parents=True, exist_ok=False)
    with TemporaryDirectory(prefix="logistics-quality-") as directory:
        work = Path(directory)
        shutil.copytree(root / "conf", work / "conf")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            (str(root), str(root / "src"), env.get("PYTHONPATH", ""))
        )
        env["COVERAGE_FILE"] = str(work / "coverage")
        commands = (
            (
                [
                    "ruff",
                    "check",
                    "src",
                    "tests",
                    "conftest.py",
                    "scripts/check_quality.py",
                ],
                root,
            ),
            (
                [
                    "black",
                    "--check",
                    "src",
                    "tests",
                    "conftest.py",
                    "scripts/check_quality.py",
                ],
                root,
            ),
            (
                [
                    "coverage",
                    "run",
                    "--source=" + str(root / "src"),
                    "-m",
                    "pytest",
                    str(root / "tests"),
                    "-q",
                ],
                work,
            ),
            (
                [
                    "coverage",
                    "json",
                    "-o",
                    str(args.report.resolve() / "coverage.json"),
                ],
                work,
            ),
        )
        for command, cwd in commands:
            result = subprocess.run(
                [sys.executable, "-m", *command],
                cwd=cwd,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            report["checks"].append(
                {
                    "command": command,
                    "exit_code": result.returncode,
                    "output": result.stdout + result.stderr,
                }
            )
            print(report["checks"][-1]["output"], flush=True)
            if result.returncode:
                break
        passed = all(check["exit_code"] == 0 for check in report["checks"])
        if passed:
            coverage = json.loads((args.report / "coverage.json").read_text())
            core = [
                value["summary"]
                for name, value in coverage["files"].items()
                if "/ui/" not in name.replace("\\", "/")
            ]
            report["whole_src_coverage"] = coverage["totals"]["percent_covered"]
            report["core_coverage"] = (
                100
                * sum(v["covered_lines"] for v in core)
                / sum(v["num_statements"] for v in core)
            )
            passed = report["core_coverage"] >= 90
        report["passed"] = passed
        (args.report / "quality.json").write_text(json.dumps(report, indent=2))
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
