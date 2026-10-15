"""Reassemble verified M02 sampled data from repository-sized parts."""

import argparse
import hashlib
import json
from pathlib import Path


def restore(directory):
    directory = Path(directory)
    meta = json.loads((directory / "payload.json").read_text())
    target = directory / "sampled.jsonl.gz"
    if (
        target.exists()
        and hashlib.sha256(target.read_bytes()).hexdigest() == meta["sha256"]
    ):
        return target
    temporary = directory / "sampled.jsonl.gz.tmp"
    digest = hashlib.sha256()
    with temporary.open("wb") as out:
        for part in meta["parts"]:
            path = directory / part["name"]
            if not path.resolve().is_relative_to(directory.resolve()):
                raise ValueError("unsafe part path")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != part["sha256"]:
                raise ValueError("part checksum mismatch")
            digest.update(data)
            out.write(data)
    if (
        digest.hexdigest() != meta["sha256"]
        or temporary.stat().st_size != meta["size_bytes"]
    ):
        raise ValueError("assembled checksum/size mismatch")
    temporary.replace(target)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    print(restore(parser.parse_args().directory))
