"""Inspect/verify the registry; promote or roll back only with manual approval."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from logistics import model_registry as mr  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inspect", "verify", "promote", "rollback"])
    parser.add_argument("--registry", default="models/registry-v1.json")
    parser.add_argument("--version")
    parser.add_argument("--approval-json", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    path = mr.safe_path(root, args.registry)
    state = json.loads(path.read_text())
    if args.action == "inspect":
        print(json.dumps(state, indent=2))
        return
    if args.action == "verify":
        versions = [args.version] if args.version else sorted(state["versions"])
        for version in versions:
            mr.verify_version(state, version, root)
        if state["active"] is not None:
            mr.active_artifact(state, root)
        print(json.dumps({"verified_versions": versions, "active": state["active"]}))
        return
    if args.version is None or args.approval_json is None:
        parser.error("--version and --approval-json are required")
    approval = json.loads(args.approval_json.read_text())
    action = mr.promote if args.action == "promote" else mr.rollback
    updated = action(state, args.version, root, approval)
    mr.write_registry(path, updated)
    print(json.dumps({"active": updated["active"], "event": updated["history"][-1]}))


if __name__ == "__main__":
    main()
