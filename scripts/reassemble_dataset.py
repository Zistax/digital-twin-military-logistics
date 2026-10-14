"""Reassemble verified dataset archives stored as small Git blobs."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def file_digest(path):
    result = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def restore(directory, output):
    directory = directory.resolve()
    manifest = json.loads((directory / "manifest.json").read_text())
    output.mkdir(parents=True, exist_ok=True)
    restored = []
    for asset in manifest["assets"]:
        if Path(asset["filename"]).name != asset["filename"]:
            raise ValueError("invalid archive filename")
        destination = output / asset["filename"]
        if destination.exists():
            if file_digest(destination) != asset["sha256"]:
                raise FileExistsError(
                    f"different archive already exists: {destination}"
                )
            restored.append(str(destination))
            continue
        temporary = destination.with_suffix(destination.suffix + ".partial")
        checksum, total = sha256(), 0
        with temporary.open("xb") as target:
            try:
                for part in asset["chunks"]:
                    source = (directory / part["path"]).resolve()
                    if not source.is_relative_to(directory):
                        raise ValueError("invalid chunk path")
                    raw = source.read_bytes()
                    if (
                        len(raw) != part["bytes"]
                        or sha256(raw).hexdigest() != part["sha256"]
                    ):
                        raise ValueError(f"chunk checksum mismatch: {source}")
                    target.write(raw)
                    checksum.update(raw)
                    total += len(raw)
                if total != asset["bytes"] or checksum.hexdigest() != asset["sha256"]:
                    raise ValueError("archive checksum mismatch")
            except BaseException:
                target.close()
                temporary.unlink(missing_ok=True)
                raise
        temporary.replace(destination)
        restored.append(str(destination))
    return restored


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({"restored": restore(args.directory, args.output)}))
