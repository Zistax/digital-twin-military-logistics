"""Release invariants: deterministic payload, no caches, integrity and cleanup."""

import json
from pathlib import Path
import sys
from types import SimpleNamespace
import zipfile

import pytest

from scripts import build_local_package as package
from scripts import local_demo as demo
from src.api.model_compat import load_legacy_artifact


def project(tmp_path):
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "src/main.py").write_text("print('demo')\n")
    (root / "requirements-local.txt").write_text("example==1.0\n")
    return root


def test_package_determinism_manifest_and_exclusions(tmp_path):
    root = project(tmp_path)
    (root / "src/__pycache__").mkdir()
    (root / "src/__pycache__/main.pyc").write_bytes(b"cache")
    (root / "reports/m02-v1").mkdir(parents=True)
    (root / "reports/m02-v1/payload.jsonl.gz").write_bytes(b"separate")
    a, b = package.build(root, tmp_path / "a.zip"), package.build(
        root, tmp_path / "b.zip"
    )
    assert a["sha256"] == b["sha256"]
    with zipfile.ZipFile(tmp_path / "a.zip") as archive:
        manifest = json.loads(archive.read("digital-twin-local/PACKAGE-MANIFEST.json"))
        assert all("__pycache__" not in name for name in archive.namelist())
        assert manifest["sha256"]["src/main.py"] == package.digest(root / "src/main.py")
        assert manifest["excluded_payloads"][0]["path"].endswith("payload.jsonl.gz")
    (root / "src/main.py").write_text("print('changed')\n")
    assert package.build(root, tmp_path / "c.zip")["sha256"] != a["sha256"]


def test_package_rejects_missing_lock_and_symlink(tmp_path):
    root = project(tmp_path)
    (root / "requirements-local.txt").unlink()
    with pytest.raises(ValueError, match="lock"):
        package.build(root, tmp_path / "a.zip")
    (root / "requirements-local.txt").write_text("example==1.0\n")
    (root / "src/link.py").symlink_to(root / "src/main.py")
    with pytest.raises(ValueError, match="symlink"):
        package.build(root, tmp_path / "a.zip")


def test_doctor_detects_corrupt_and_unsafe_package(tmp_path, monkeypatch):
    root = project(tmp_path)
    (root / "models").mkdir()
    (root / "models/registry-v1.json").write_text('{"active": null, "versions": {}}')
    (root / "PACKAGE-MANIFEST.json").write_text(
        json.dumps({"sha256": {"src/main.py": "wrong", "../outside": "wrong"}})
    )
    monkeypatch.setattr(demo.importlib.metadata, "version", lambda _: "1.0")
    result = demo.doctor(root)
    assert not result["passed"] and result["package_manifest_checked"]
    assert len(result["issues"]) == 2
    monkeypatch.setattr(demo.importlib.metadata, "version", lambda _: "2.0")
    assert "expected 1.0" in demo.doctor(root)["issues"][0]


def test_historical_module_conflict_is_explicit(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "logistics", SimpleNamespace(__file__="/different/__init__.py")
    )
    with pytest.raises(ValueError, match="conflicting historical"):
        load_legacy_artifact(Path("unused.joblib"))


def test_launcher_stops_children_after_readiness_failure(monkeypatch):
    children = []

    class Child:
        stopped = False

        def poll(self):
            return 0 if self.stopped else None

        def terminate(self):
            self.stopped = True

        def wait(self, timeout):
            assert self.stopped

        def kill(self):
            self.stopped = True

    def popen(*args, **kwargs):
        child = Child()
        children.append(child)
        return child

    def fail(*args, **kwargs):
        raise RuntimeError("readiness failed")

    monkeypatch.setattr(demo.subprocess, "Popen", popen)
    monkeypatch.setattr(demo, "wait_http", fail)
    with pytest.raises(RuntimeError, match="readiness failed"):
        demo.serve(demo.free_port(), demo.free_port(), True)
    assert len(children) == 1 and children[0].stopped
    with pytest.raises(ValueError, match="distinct"):
        demo.serve(8000, 8000, True)
