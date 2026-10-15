import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

import joblib
import pytest

from logistics import initial_prediction as ip
from logistics import rolling_prediction as rp
from tests.test_rolling_prediction import dataset


def runner():
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location(
        "m03_runner", scripts / "evaluate_m03.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_table_verification_rejects_corruption(tmp_path):
    module = runner()
    path = tmp_path / "table.zip"
    data = b'{"a":1}\n'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("prefix/table", data)
    meta = {"files": {"table": {"sha256": hashlib.sha256(data).hexdigest(), "rows": 1}}}
    with zipfile.ZipFile(path) as z:
        assert module.verified_table(z, "prefix/", meta, "table") == [{"a": 1}]
        meta["files"]["table"]["rows"] = 2
        with pytest.raises(ValueError, match="checksum/count"):
            module.verified_table(z, "prefix/", meta, "table")


def test_freeze_evaluation_and_registry_end_to_end_on_synthetic_fixture(
    tmp_path, monkeypatch
):
    module = runner()
    tr, ct = dataset()
    ca, cc = dataset("calibration", "c")
    te, ce = dataset("test", "t")
    for row in te + ce:
        row["profile"] = "regular"
    for r in te:
        r["key"][0] = "test-s"
        r["creation"]["simulation_id"] = "test-s"
        r["observation"]["simulation_id"] = "test-s"
    for r in ce:
        r["key"][0] = "test-s"
        r["observation"]["simulation_id"] = "test-s"
    initial = ip.fit_final(ct, cc, "logistic", "median")
    model = rp.fit_predictor(
        tr,
        ca,
        {"classification": "logistic", "pre": "median", "post": "median"},
        initial,
    )
    rp.calibrate_intervals(model, ca, cc)
    for folder, name, obj in [
        ("m01-v1", "initial_predictor.joblib", initial),
        ("m02-v1", "rolling_predictor.joblib", model),
    ]:
        target = tmp_path / "reports" / folder
        target.mkdir(parents=True)
        joblib.dump(obj, target / name)
        (target / "report.json").write_text(
            json.dumps(
                {
                    "artifacts": {name: module.registry.sha256(target / name)},
                    "implementation_sha256": {},
                    "versions": {},
                }
            )
        )
    prepared = tmp_path / "reports/m02-v1/data"
    prepared.mkdir()
    path = prepared / "sampled.jsonl.gz"
    with gzip.open(path, "wt") as f:
        for r in tr + ca:
            f.write(json.dumps(r) + "\n")
    (prepared / "manifest.json").write_text(
        json.dumps({"sha256": module.registry.sha256(path)})
    )
    source = tmp_path / "reports/d03-batch-v1"
    source.mkdir()
    for name in ("plan.json", "split_manifest.json"):
        (source / name).write_text("{}")
    quality = tmp_path / "reports/quality-m03-final-20261015"
    quality.mkdir()
    (quality / "quality.json").write_text('{"passed":true}')
    protocol = tmp_path / "docs/protocollo-m03-v1.md"
    protocol.parent.mkdir()
    protocol.write_text("frozen fixture")
    monkeypatch.setattr(module, "files_to_freeze", lambda repo: [protocol])
    monkeypatch.setattr(module.ip, "load_creation", lambda root: (ct + cc, []))
    out = tmp_path / "reports/m03-v1"
    out.mkdir()
    module.freeze(tmp_path, out)
    with pytest.raises(ValueError, match="already frozen"):
        module.freeze(tmp_path, out)
    calls = []

    def load_test(repo, archives):
        calls.append(True)
        return ce, te, [{"native_rolling": len(te), "group": f"t{i}"} for i in range(6)]

    monkeypatch.setattr(module, "load_test", load_test)
    module.evaluate(tmp_path, out, tmp_path)
    report = json.loads((out / "report.json").read_text())
    assert len(calls) == 1 and report["test_consumed"]
    assert len(report["channels_with_policy"]) == 5
    assert not report["promotion"]["eligible"]
    state = json.loads((tmp_path / "models/registry-v1.json").read_text())
    assert state["active"] is None and len(state["versions"]) == 2
    with pytest.raises(ValueError, match="already attempted"):
        module.evaluate(tmp_path, out, tmp_path)
    protocol.write_text("changed")
    with pytest.raises(ValueError, match="frozen input changed"):
        module.evaluate(tmp_path, out, tmp_path)
    assert len(calls) == 1
