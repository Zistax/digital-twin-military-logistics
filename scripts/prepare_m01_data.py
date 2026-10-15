"""Verify four published D03 archives and extract only creation development data."""

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ARCHIVE_SHA256 = (
    "b94f15a78e35359055c9cd374e58b022d1a4b94e12c9908ab460c0f056c3c7f5",
    "c96e0b1ad5239c4aa698172eedd832c6e6fbfa783a914730859b107328c9e7fb",
    "8c6771bbf211b40be3044ad9821dff03dff8da6a4bc888f5be9c5071e387e27b",
    "1140b0352ab5ec6ad02336c0afdf5df19901b7fe9bc91984b7cc68b342c169e1",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = [args.archives / f"Dataset_D03_Parte_{i}_di_4.zip" for i in range(1, 5)]
    for path, expected in zip(paths, ARCHIVE_SHA256):
        with path.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != expected:
                raise ValueError(f"archive checksum mismatch: {path.name}")
    with zipfile.ZipFile(paths[0]) as archive:
        metadata = {
            name: archive.read("d03-batch-v1/" + name)
            for name in ("plan.json", "split_manifest.json")
        }
    split = json.loads(metadata["split_manifest.json"])
    expected = {}
    for name in ("training", "calibration"):
        for record in split["sets"][name]:
            expected[record["bundle"] + "/manifest.json"] = record["manifest_sha256"]
    written = set()
    args.output.mkdir(parents=True, exist_ok=True)
    for path in paths:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            for relative, checksum in expected.items():
                name = "d03-batch-v1/" + relative
                if name not in names:
                    continue
                manifest_bytes = archive.read(name)
                if hashlib.sha256(manifest_bytes).hexdigest() != checksum:
                    raise ValueError("manifest checksum mismatch")
                manifest = json.loads(manifest_bytes)
                folder = relative.rsplit("/", 1)[0]
                files = {relative: manifest_bytes}
                for tail in ("observations.jsonl", "labels.jsonl"):
                    data = archive.read("d03-batch-v1/" + folder + "/" + tail)
                    if (
                        hashlib.sha256(data).hexdigest()
                        != manifest["files"][tail]["sha256"]
                    ):
                        raise ValueError("table checksum mismatch")
                    files[folder + "/" + tail] = data
                for relative_file, data in files.items():
                    target = args.output / relative_file
                    if not target.resolve().is_relative_to(args.output.resolve()):
                        raise ValueError("unsafe archive path")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                written.add(relative)
    if written != set(expected):
        raise ValueError("missing development bundles")
    for name, data in metadata.items():
        (args.output / name).write_bytes(data)
    print(json.dumps({"verified_bundles": len(written), "test_tables_extracted": 0}))


if __name__ == "__main__":
    main()
