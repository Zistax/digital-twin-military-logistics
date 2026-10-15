"""Check, exercise, or launch the local native demonstration (Python 3.12)."""

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def doctor(root=ROOT):
    issues = []
    if sys.version_info[:2] != (3, 12):
        issues.append("Use Python 3.12 for the validated local environment")
    for line in (root / "requirements-local.txt").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==")
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = "missing"
        if actual != version:
            issues.append(f"{name}: expected {version}, found {actual}")
    from src.logistics.model_registry import verify_version

    registry = json.loads((root / "models/registry-v1.json").read_text())
    for version in registry["versions"]:
        try:
            verify_version(registry, version, root)
        except (OSError, ValueError, KeyError) as exc:
            issues.append(f"{version}: {exc}")
    manifest_path = root / "PACKAGE-MANIFEST.json"
    if manifest_path.exists():
        for relative, expected in json.loads(manifest_path.read_text())[
            "sha256"
        ].items():
            path = (root / relative).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                issues.append("missing or unsafe package file: " + relative)
            elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                issues.append("package checksum mismatch: " + relative)
    return {
        "passed": not issues,
        "python": sys.version,
        "executable": sys.executable,
        "virtual_environment": sys.prefix != sys.base_prefix,
        "issues": issues,
        "active_model": registry["active"],
        "package_manifest_checked": manifest_path.exists(),
    }


def smoke():
    from src.api.logistics import (
        Advance,
        Cancel,
        NewMission,
        NewSession,
        SessionStore,
    )
    from fastapi import HTTPException

    store = SessionStore()
    view = store.create(NewSession(forecast_mode="experimental"))
    sid = view["session_id"]
    created = NewMission(
        command_id="mission",
        expected_revision=0,
        origin_id="central-a",
        destination_id="local-a",
        quantities={"food-small": 10},
        deadline_s=650,
    )
    view = store.command(sid, "mission", created)
    assert view["missions"][0]["lines"][0]["minimum"] == 8
    assert store.command(sid, "mission", created) == view
    view = store.command(
        sid,
        "advance",
        Advance(command_id="advance", expected_revision=1, target_s=2000),
    )
    history = view["missions"][0]["prediction_history"]
    assert any(
        r["observed_s"] == 650 and "deadline" in r.get("trigger_reasons", [])
        for r in history
    )
    assert any(
        r["observed_s"] == 1800 and "periodic" in r.get("trigger_reasons", [])
        for r in history
    )
    view = store.command(
        sid,
        "cancel",
        Cancel(
            command_id="cancel",
            expected_revision=2,
            mission_id="manual:mission",
            reason="local smoke test",
        ),
    )
    assert view["analysis"]["cancelled"] == 1
    assert view["missions"][0]["prediction"]["status"] == "stopped"
    store.delete(sid)
    try:
        store.create(NewSession(forecast_mode="approved"))
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("unapproved model accepted")
    # Native operational recovery with deterministic inputs, no future information.
    from datetime import datetime, timezone
    from decimal import Decimal
    from src.logistics.calendars import Calendar
    from src.logistics.core import Mission, MissionLine
    from src.logistics.operations import DepotOperations
    from src.logistics.recovery import RecoveryWarehouse
    from src.logistics.roads import Network, Node, Road
    from src.logistics.warehouse import Item, Store, Vehicle

    w = RecoveryWarehouse(
        "smoke",
        [Item("a", Decimal(1), Decimal(1), 30)],
        [Store(d, Decimal(100), Decimal(0)) for d in ("origin", "dest")],
        [Vehicle(v, "origin", Decimal(100), Decimal(100)) for v in ("v0", "v1")],
        network=Network(
            [Node("origin", 0, 0), Node("dest", 10, 0)], [Road("origin", "dest", 30)]
        ),
        epoch=datetime(2026, 10, 5, tzinfo=timezone.utc),
        operations={
            d: DepotOperations(Calendar(tuple((day, 0, 86400) for day in range(7))))
            for d in ("origin", "dest")
        },
    )
    w.receive("stock", 0, "origin", {"a": 20})
    w.register(
        "register",
        0,
        Mission(
            "smoke",
            "m",
            "origin",
            "dest",
            0,
            2500,
            (MissionLine("a", 10, Decimal(".9")),),
        ),
    )
    w.schedule("schedule", 0, "m")
    w.advance("step", 1000)
    w.breakdown("breakdown", 1000, "v0", False, 86400)
    assert w.observed_incidents()["requests"]["request-1"]["status"] == "pending"
    w.decide("approve", 1000, "request-1", "approve")
    w.advance("dispatch", 1000)
    assert w.observed_incidents()["requests"]["request-1"]["status"] in (
        "approved",
        "in_progress",
    )
    return {
        "passed": True,
        "checks": [
            "native_mission",
            "idempotency",
            "exact_deadline",
            "periodic_forecast",
            "cancellation",
            "approved_model_refused",
            "manual_recovery",
        ],
        "forecast_mode": "experimental_not_promoted",
    }


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_http(url, process, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("server exited before readiness")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.2)
    raise RuntimeError("server readiness timed out")


def check_ui(api_url):
    from streamlit.testing.v1 import AppTest

    previous = os.environ.get("LOGISTICS_API_URL")
    os.environ["LOGISTICS_API_URL"] = api_url
    try:
        ui = AppTest.from_file(
            str(ROOT / "src/ui/dashboard.py"), default_timeout=30
        ).run()
        assert not ui.exception
        next(
            c for c in ui.checkbox if c.label.startswith("Abilita candidato")
        ).check().run()
        assert not ui.exception
        for label in (
            "Crea sessione",
            "Registra missione",
            "Avanza di un'ora",
            "Aggiorna dati",
            "Chiudi sessione",
        ):
            next(b for b in ui.button if b.label == label).click().run()
            assert not ui.exception, ui.exception
        assert "view" not in ui.session_state
    finally:
        if previous is None:
            os.environ.pop("LOGISTICS_API_URL", None)
        else:
            os.environ["LOGISTICS_API_URL"] = previous


def serve(api_port, ui_port, check_only=False):
    if not 0 < api_port < 65536 or not 0 < ui_port < 65536 or api_port == ui_port:
        raise ValueError("two distinct valid ports required")
    # Fail before contacting an unrelated server already listening on either port.
    with socket.socket() as api_socket, socket.socket() as ui_socket:
        api_socket.bind(("127.0.0.1", api_port))
        ui_socket.bind(("127.0.0.1", ui_port))
    children = []
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    try:
        children.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "src.api.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                    "--workers",
                    "1",
                ],
                cwd=ROOT,
                env=env,
            )
        )
        wait_http(f"http://127.0.0.1:{api_port}/health", children[0])
        # Pass the selected API port to the dashboard.
        env["LOGISTICS_API_URL"] = f"http://127.0.0.1:{api_port}"
        children.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "src/ui/dashboard.py",
                    "--server.address",
                    "127.0.0.1",
                    "--server.port",
                    str(ui_port),
                    "--server.headless",
                    "true",
                    "--browser.gatherUsageStats",
                    "false",
                ],
                cwd=ROOT,
                env=env,
            )
        )
        wait_http(f"http://127.0.0.1:{ui_port}/_stcore/health", children[1])
        print(
            json.dumps(
                {
                    "ready": True,
                    "api": f"http://127.0.0.1:{api_port}",
                    "ui": f"http://127.0.0.1:{ui_port}",
                }
            ),
            flush=True,
        )
        if check_only:
            check_ui(f"http://127.0.0.1:{api_port}")
        else:
            while all(p.poll() is None for p in children):
                time.sleep(0.3)
            raise RuntimeError("a server stopped unexpectedly")
    finally:
        for p in children:
            if p.poll() is None:
                p.terminate()
        for p in children:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["doctor", "smoke", "serve", "check-servers"])
    parser.add_argument("--report", type=Path)
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--ui-port", type=int, default=8501)
    args = parser.parse_args()
    os.chdir(ROOT)
    result = doctor()
    if result["passed"] and args.action == "smoke":
        result["smoke"] = smoke()
    if result["passed"] and args.action in ("serve", "check-servers"):
        serve(args.api_port, args.ui_port, args.action == "check-servers")
        result["servers_checked"] = True
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
