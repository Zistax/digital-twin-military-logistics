import hashlib
import json

import pytest

from scripts.reassemble_dataset import restore


def prepare(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    first, second = b"archive-first-half", b"archive-second-half"
    (source / "first.bin").write_bytes(first)
    (source / "second.bin").write_bytes(second)
    manifest = {
        "assets": [
            {
                "filename": "test.zip",
                "bytes": len(first + second),
                "sha256": hashlib.sha256(first + second).hexdigest(),
                "chunks": [
                    {
                        "path": name,
                        "bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                    for name, raw in (("first.bin", first), ("second.bin", second))
                ],
            }
        ]
    }
    (source / "manifest.json").write_text(json.dumps(manifest))
    return source, manifest, first + second


def test_archive_reassembly_and_idempotent_resume(tmp_path):
    source, _, expected = prepare(tmp_path)
    output = tmp_path / "out"
    paths = restore(source, output)
    assert (output / "test.zip").read_bytes() == expected
    assert restore(source, output) == paths


def test_corrupt_chunk_does_not_publish_partial_archive(tmp_path):
    source, _, _ = prepare(tmp_path)
    (source / "second.bin").write_bytes(b"damaged")
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="chunk checksum"):
        restore(source, output)
    assert not list(output.iterdir())


def test_wrong_whole_archive_checksum_is_rejected(tmp_path):
    source, manifest, _ = prepare(tmp_path)
    manifest["assets"][0]["sha256"] = "0" * 64
    (source / "manifest.json").write_text(json.dumps(manifest))
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="archive checksum"):
        restore(source, output)
    assert not list(output.iterdir())
