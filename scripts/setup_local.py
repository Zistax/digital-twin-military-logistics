"""Create/reuse a dedicated Python 3.12 venv and install the local lock."""

import argparse
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", type=Path, default=ROOT / ".venv")
    parser.add_argument("--wheelhouse", type=Path)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.error("use Python 3.12 (Windows: py -3.12)")
    target = args.venv.resolve()
    if target.exists() and not (target / "pyvenv.cfg").exists():
        parser.error("target exists and is not a virtual environment")
    venv.EnvBuilder(with_pip=True, clear=False, system_site_packages=False).create(
        target
    )
    python = target / (
        "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    )
    command = [
        str(python),
        "-m",
        "pip",
        "install",
        "-r",
        str(ROOT / "requirements-local.txt"),
    ]
    if args.wheelhouse:
        command += ["--no-index", "--find-links", str(args.wheelhouse.resolve())]
    subprocess.run(command, cwd=ROOT, check=True)
    subprocess.run([str(python), "-m", "pip", "check"], cwd=ROOT, check=True)
    subprocess.run(
        [str(python), str(ROOT / "scripts/local_demo.py"), "doctor"],
        cwd=ROOT,
        check=True,
    )
    print(f"Ready: {python} scripts/local_demo.py serve")


if __name__ == "__main__":
    main()
