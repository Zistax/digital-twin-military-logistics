"""Predict from observable snapshots using a verified local M02 artifact."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import joblib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--example", choices=["pre", "post"])
    args = parser.parse_args()
    report = json.loads((args.model.parent / "report.json").read_text())
    digest = hashlib.sha256(args.model.read_bytes()).hexdigest()
    if digest != report["artifacts"][args.model.name]:
        raise ValueError("model checksum mismatch")
    model = joblib.load(args.model)
    request = json.loads(args.request.read_text())
    if args.example:
        request = request[args.example]
    result = (
        model.predict(request["creation"], request["observation"])
        if "observation" in request
        else model.predict_creation(request["creation"])
    )
    result.update(model_sha256=digest, snapshot=request)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
