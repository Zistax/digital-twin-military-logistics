"""Do not label a changed or unsupported source bundle as container-verified."""

import json
import hashlib

import pytest

from scripts import build_demo_package as package


@pytest.mark.parametrize(
    "report,reason",
    [
        ({"passed": False}, "passing container report"),
        ({"passed": True}, "source checksums required"),
        (
            {"passed": True, "validated_source_sha256": {"../outside": "bad"}},
            "unsafe evidence path",
        ),
        (
            {"passed": True, "validated_source_sha256": {"src/api/demo_app.py": "bad"}},
            "evidence is stale",
        ),
    ],
)
@pytest.mark.parametrize("load_version", [False, True])
def test_container_label_requires_current_safe_evidence(
    tmp_path, monkeypatch, report, reason, load_version
):
    monkeypatch.setattr(
        package, "package_files", lambda root: (["src/api/demo_app.py"], [])
    )
    if load_version:
        launcher = tmp_path / "scripts/run_demo.py"
        launcher.parent.mkdir(parents=True)
        launcher.write_text("launcher")
        load_path = tmp_path / "reports/r02-load-v1/verification.json"
        load_path.parent.mkdir(parents=True)
        load_path.write_text(
            json.dumps(
                {
                    "passed": True,
                    "validated_runtime_sha256": {
                        "scripts/run_demo.py": hashlib.sha256(
                            launcher.read_bytes()
                        ).hexdigest()
                    },
                }
            )
        )
    report_name = (
        "reports/r02-load-v1/container-verification.json"
        if load_version
        else "reports/r02-container-v1/verification.json"
    )
    path = tmp_path / report_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report))
    source = tmp_path / "src/api/demo_app.py"
    source.parent.mkdir(parents=True)
    source.write_text("current source")
    with pytest.raises(ValueError, match=reason):
        package.build(
            tmp_path,
            tmp_path / "demo.zip",
            include_container_report=True,
            include_load_report=load_version,
        )
    assert not (tmp_path / "demo.zip").exists()


@pytest.mark.parametrize(
    "report,reason",
    [
        ({"passed": False}, "passing load report"),
        ({"passed": True}, "load runtime checksums"),
        (
            {"passed": True, "validated_runtime_sha256": {"../outside": "bad"}},
            "unsafe load evidence path",
        ),
        (
            {
                "passed": True,
                "validated_runtime_sha256": {"scripts/run_demo.py": "bad"},
            },
            "load evidence is stale",
        ),
    ],
)
def test_load_label_requires_current_runtime(tmp_path, monkeypatch, report, reason):
    monkeypatch.setattr(package, "package_files", lambda root: ([], []))
    path = tmp_path / "reports/r02-load-v1/verification.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(report))
    launcher = tmp_path / "scripts/run_demo.py"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("launcher")
    with pytest.raises(ValueError, match=reason):
        package.build(tmp_path, tmp_path / "demo.zip", include_load_report=True)
    assert not (tmp_path / "demo.zip").exists()
