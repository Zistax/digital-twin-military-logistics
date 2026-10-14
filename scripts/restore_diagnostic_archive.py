"""Restore the preserved diagnostic ZIP from verified binary chunks."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def restore(directory, output=None):
    manifest = json.loads((directory / "manifest.json").read_text())
    output = output or directory.parent / manifest["filename"]
    temporary = output.with_suffix(output.suffix + ".reconstructing")
    total, checksum = 0, sha256()
    try:
        with temporary.open("xb") as target:
            for part in manifest["parts"]:
                data = (directory / part["name"]).read_bytes()
                if (
                    len(data) != part["bytes"]
                    or sha256(data).hexdigest() != part["sha256"]
                ):
                    raise ValueError("diagnostic chunk checksum mismatch")
                target.write(data)
                checksum.update(data)
                total += len(data)
        if total != manifest["bytes"] or checksum.hexdigest() != manifest["sha256"]:
            raise ValueError("diagnostic archive checksum mismatch")
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return {"output": str(output), "bytes": total, "sha256": checksum.hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(restore(args.directory, args.output)))
