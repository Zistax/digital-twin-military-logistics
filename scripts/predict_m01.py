"""Predict from a creation-v1 JSON observation and a locally trained M01 model."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import joblib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--observation", required=True, type=Path)
    args = parser.parse_args()
    report = json.loads((args.model.parent / "report.json").read_text())
    actual = hashlib.sha256(args.model.read_bytes()).hexdigest()
    if actual != report["artifacts"][args.model.name]:
        raise ValueError("model checksum mismatch")
    model = joblib.load(args.model)
    print(
        json.dumps(
            model.predict(json.loads(args.observation.read_text())),
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
