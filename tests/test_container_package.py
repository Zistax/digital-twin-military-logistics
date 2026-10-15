"""Do not label a changed or unsupported source bundle as container-verified."""

import json

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
def test_container_label_requires_current_safe_evidence(
    tmp_path, monkeypatch, report, reason
):
    monkeypatch.setattr(
        package, "package_files", lambda root: (["src/api/demo_app.py"], [])
    )
    path = tmp_path / "reports/r02-container-v1/verification.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(report))
    source = tmp_path / "src/api/demo_app.py"
    source.parent.mkdir(parents=True)
    source.write_text("current source")
    with pytest.raises(ValueError, match=reason):
        package.build(tmp_path, tmp_path / "demo.zip", include_container_report=True)
    assert not (tmp_path / "demo.zip").exists()
