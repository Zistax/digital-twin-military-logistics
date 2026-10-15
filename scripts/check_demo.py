"""Verify the restricted demo over real HTTP, including a server restart."""

import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def verify():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    latencies = []

    def request(path, method="GET", body=None, token=None, expected=200, extra=None):
        headers = dict(extra or {})
        if token:
            headers["Authorization"] = "Bearer " + token
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            origin + path, data=data, headers=headers, method=method
        )
        before = time.perf_counter()
        try:
            response = urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            assert response.status == expected, (path, response.status, expected)
            raw = response.read()
        latencies.append(
            {"route": path, "seconds": round(time.perf_counter() - before, 3)}
        )
        return json.loads(raw) if raw else {}

    with TemporaryDirectory(prefix="r02-http-") as temp:
        secret = secrets.token_urlsafe(48)
        env = dict(
            os.environ,
            DEMO_ADMIN_SECRET=secret,
            DEMO_DATABASE=str(Path(temp) / "demo.db"),
            DEMO_PUBLIC_ORIGIN=origin,
            OMP_NUM_THREADS="1",
            OPENBLAS_NUM_THREADS="1",
        )
        env.pop("PYTHONPATH", None)
        command = [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api.demo_app:create_demo_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
            "--no-proxy-headers",
        ]

        def start():
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                deadline = time.monotonic() + 25
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError("demo exited before readiness")
                    try:
                        request("/health")
                        return process
                    except (OSError, urllib.error.URLError):
                        time.sleep(0.1)
                raise RuntimeError("demo readiness timed out")
            except BaseException:
                stop(process)
                raise

        def stop(process):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

        process = start()
        try:
            a = request("/demo/access", "POST", expected=201)["token"]
            b = request("/demo/access", "POST", expected=201)["token"]
            first = request(
                "/v1/sessions", "POST", {"forecast_mode": "experimental"}, a, 201
            )
            second = request("/v1/sessions", "POST", {}, b, 201)
            sid = first["session_id"]
            request(f"/v1/sessions/{sid}", token=b, expected=404)
            request("/admin/status", token=a, expected=403)
            request(
                "/demo/access",
                "POST",
                extra={"Origin": "https://untrusted.example"},
                expected=403,
            )
            mission = {
                "command_id": "http-mission",
                "expected_revision": 0,
                "origin_id": "central-a",
                "destination_id": "local-a",
                "quantities": {"food-small": 10},
                "deadline_s": 1200,
            }
            created = request(f"/v1/sessions/{sid}/missions", "POST", mission, a)
            advanced = request(
                f"/v1/sessions/{sid}/advance",
                "POST",
                {"command_id": "http-advance", "expected_revision": 1, "target_s": 300},
                a,
            )
            assert advanced["observed_s"] == 300
            stop(process)
            process = start()
            assert request(f"/v1/sessions/{sid}", token=a) == advanced
            assert (
                request(f"/v1/sessions/{sid}/missions", "POST", mission, a) == created
            )
            request(
                f"/v1/sessions/{sid}/missions",
                "POST",
                {**mission, "deadline_s": 1300},
                a,
                409,
            )
            assert request(f"/v1/sessions/{sid}", token=a) == advanced
            request(f"/v1/sessions/{sid}", "DELETE", token=a, expected=204)
            request("/demo/access", "DELETE", token=a, expected=204)
            request(f"/v1/sessions/{sid}", token=a, expected=401)
            assert request(f"/v1/sessions/{second['session_id']}", token=b) == second
            request("/demo/access", "DELETE", token=b, expected=204)
            assert request("/admin/status", token=secret)["sessions"] == 0
        finally:
            stop(process)
    return {
        "passed": True,
        "python": sys.version,
        "platform": sys.platform,
        "source_root": str(ROOT),
        "real_http": True,
        "real_experimental_worker": True,
        "restart_persistence": True,
        "durable_retry": True,
        "conflicting_retry_rejected": True,
        "cross_owner_rejected": True,
        "admin_protected": True,
        "untrusted_origin_rejected": True,
        "revocation_cascades": True,
        "latencies": latencies,
        "online_published": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = verify()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": True, "requests": len(result["latencies"])}))


if __name__ == "__main__":
    main()
