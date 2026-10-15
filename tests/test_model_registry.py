import json

import pytest

from logistics import model_registry as mr

APPROVAL = {"approved": True, "approved_by": "reviewer", "reason": "manual review"}


def entry(root, version, eligible=True):
    artifact = root / (version + ".bin")
    artifact.write_bytes(version.encode())
    evaluation = root / (version + ".json")
    evaluation.write_text(json.dumps({"promotion": {"eligible": eligible}}))
    return {
        "artifact": {"path": artifact.name, "sha256": mr.sha256(artifact)},
        "evaluation": {"path": evaluation.name, "sha256": mr.sha256(evaluation)},
    }


def test_registration_is_immutable_and_not_active(tmp_path):
    e = entry(tmp_path, "v1")
    r = mr.register_candidate(mr.empty_registry(), "v1", e, tmp_path)
    assert r["active"] is None
    assert mr.register_candidate(r, "v1", e, tmp_path) == r
    with pytest.raises(ValueError, match="immutable"):
        mr.register_candidate(r, "v1", dict(e, status="changed"), tmp_path)
    r["registry_version"] = 2
    with pytest.raises(ValueError, match="unsupported"):
        mr.register_candidate(r, "v2", e, tmp_path)


def test_manual_promotion_and_verified_rollback(tmp_path):
    r = mr.empty_registry()
    for v in ("v1", "v2"):
        r = mr.register_candidate(r, v, entry(tmp_path, v), tmp_path)
    with pytest.raises(ValueError, match="no manually"):
        mr.active_artifact(r, tmp_path)
    with pytest.raises(ValueError, match="explicit approver"):
        mr.promote(r, "v1", tmp_path, {"approved": True})
    with pytest.raises(ValueError, match="never active"):
        mr.rollback(r, "v1", tmp_path, APPROVAL)
    r = mr.promote(r, "v1", tmp_path, APPROVAL)
    assert mr.active_artifact(r, tmp_path) == tmp_path / "v1.bin"
    r = mr.promote(r, "v2", tmp_path, APPROVAL)
    r = mr.rollback(r, "v1", tmp_path, APPROVAL)
    assert r["active"] == "v1" and r["history"][-1]["event"] == "rollback"
    path = tmp_path / "registry.json"
    mr.write_registry(path, r)
    assert json.loads(path.read_text()) == r


def test_failed_gate_cannot_be_overridden_by_approval(tmp_path):
    r = mr.register_candidate(
        mr.empty_registry(), "bad", entry(tmp_path, "bad", False), tmp_path
    )
    with pytest.raises(ValueError, match="did not pass"):
        mr.promote(r, "bad", tmp_path, APPROVAL)
    assert r["active"] is None


@pytest.mark.parametrize("name", ["artifact", "evaluation"])
def test_checksum_change_blocks_use(tmp_path, name):
    e = entry(tmp_path, "v1")
    r = mr.register_candidate(mr.empty_registry(), "v1", e, tmp_path)
    (tmp_path / e[name]["path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        mr.promote(r, "v1", tmp_path, APPROVAL)


def test_reference_and_path_guards(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        mr.safe_path(tmp_path, "../outside")
    with pytest.raises(ValueError, match="outside"):
        mr.safe_path(tmp_path, str(tmp_path / "absolute"))
    ref = tmp_path / "protocol"
    ref.write_text("fixed")
    e = entry(tmp_path, "v1")
    e["references"] = {"protocol": {"path": "protocol", "sha256": mr.sha256(ref)}}
    r = mr.register_candidate(mr.empty_registry(), "v1", e, tmp_path)
    ref.write_text("changed")
    with pytest.raises(ValueError, match="reference checksum"):
        mr.verify_version(r, "v1", tmp_path)
