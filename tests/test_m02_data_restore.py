import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def helper():
    path = Path(__file__).resolve().parents[1] / "scripts/restore_m02_data.py"
    spec = importlib.util.spec_from_file_location("restore_m02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reassembly_checks_parts_and_preserves_destination(tmp_path):
    data = b"verified sampled dataset"
    pieces = [data[:7], data[7:]]
    parts = []
    for i, piece in enumerate(pieces):
        name = f"part{i}"
        (tmp_path / name).write_bytes(piece)
        parts.append({"name": name, "sha256": hashlib.sha256(piece).hexdigest()})
    (tmp_path / "payload.json").write_text(
        json.dumps(
            {
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
                "parts": parts,
            }
        )
    )
    module = helper()
    target = module.restore(tmp_path)
    assert target.read_bytes() == data
    assert module.restore(tmp_path) == target
    target.write_bytes(b"previous file")
    (tmp_path / "part1").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="part checksum"):
        module.restore(tmp_path)
    assert target.read_bytes() == b"previous file"


def test_reassembly_rejects_paths_outside_payload(tmp_path):
    (tmp_path / "payload.json").write_text(
        json.dumps(
            {
                "sha256": "0" * 64,
                "size_bytes": 0,
                "parts": [{"name": "../outside", "sha256": "0" * 64}],
            }
        )
    )
    with pytest.raises(ValueError, match="unsafe part path"):
        helper().restore(tmp_path)
