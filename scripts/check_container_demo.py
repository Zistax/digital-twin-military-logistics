"""Verify a disposable Compose deployment over real HTTP; never export tokens."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def verify(project, port):
    env = dict(os.environ, DEMO_PORT=str(port))
    compose = ["docker", "compose", "-p", project, "-f", "deploy/compose.yaml"]

    def command(args, payload=None):
        result = subprocess.run(
            args,
            cwd=ROOT,
            env=env,
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=120,
        )
        return result.stdout.strip()

    cid = command(compose + ["ps", "-q", "demo"])
    if not cid or "\n" in cid:
        raise ValueError("exactly one running test container required")
    inspection = json.loads(command(["docker", "inspect", cid]))[0]
    host = inspection["HostConfig"]
    assert host["PortBindings"] == {
        "8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(port)}]
    }
    assert host["ReadonlyRootfs"] is True
    assert host["Memory"] == 768 * 1024 * 1024 and host["NanoCpus"] == 10**9
    assert host["PidsLimit"] == 64 and "ALL" in host["CapDrop"]
    assert any("no-new-privileges" in s for s in host["SecurityOpt"])
    assert inspection["Config"]["User"] == "demo"
    assert inspection["State"]["Health"]["Status"] == "healthy"
    volume = next(
        m["Name"] for m in inspection["Mounts"] if m["Destination"] == "/app/runtime"
    )

    def internal(code, data=None):
        return json.loads(
            command(
                ["docker", "exec", "-i", cid, "python", "-c", code],
                json.dumps(data) if data is not None else None,
            )
        )

    environment = internal("""
import json,os,platform,stat,sys
from pathlib import Path
from importlib.metadata import version
key=Path('/app/runtime/demo-admin.key')
try:
    Path('/app/rootfs-write-test').write_text('test')
    readonly=False
except OSError:
    readonly=True
print(json.dumps({'python':sys.version,'platform':platform.platform(),'uid':os.getuid(),
    'admin_key_mode':oct(stat.S_IMODE(key.stat().st_mode)),
    'admin_key_uid':key.stat().st_uid,'rootfs_write_rejected':readonly,
    'versions':{n:version(n) for n in [
        'numpy','scipy','scikit-learn','fastapi','uvicorn']}}))
""")
    assert environment["uid"] == 10001 and environment["admin_key_uid"] == 10001
    assert (
        environment["admin_key_mode"] == "0o600"
        and environment["rootfs_write_rejected"]
    )
    pip_check = command(["docker", "exec", cid, "python", "-m", "pip", "check"])
    watched = []
    for folder in (
        "src",
        "conf",
        "models",
        "reports/m01-v1",
        "reports/m02-v1",
        "reports/m03-v1",
    ):
        for path in (ROOT / folder).rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.suffix in (".pyc", ".pyo", ".zip") or path.name.endswith(
                (".jsonl", ".jsonl.gz")
            ):
                continue
            if folder.startswith("reports/") and "data" in path.relative_to(ROOT).parts:
                continue
            watched.append(path.relative_to(ROOT).as_posix())
    watched += [
        "requirements-local.txt",
        "docs/protocollo-m03-v1.md",
        "LICENSE",
        "scripts/run_demo.py",
        "reports/r01-v1/pilot-summary.json",
    ]
    image_hashes = internal(
        """
import hashlib,json,sys
from pathlib import Path
names=json.load(sys.stdin)['paths']
print(json.dumps({p:hashlib.sha256((Path('/app')/p).read_bytes()).hexdigest()
    for p in names}))
""",
        {"paths": sorted(set(watched))},
    )
    for name, expected in image_hashes.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    source_hashes = dict(image_hashes)
    for name in ("deploy/Dockerfile", "deploy/compose.yaml"):
        source_hashes[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()

    def admin():
        args = [
            "docker",
            "exec",
            "-e",
            "DEMO_PUBLIC_ORIGIN=http://127.0.0.1:8080",
            cid,
            "python",
            "scripts/run_demo.py",
            "--status",
        ]
        return json.loads(command(args))

    initial = admin()
    assert (
        initial["sessions"] == initial["leases"] == 0
    ), "use a dedicated empty test deployment"
    latencies = []
    origin = f"http://127.0.0.1:{port}"

    def request(path, method="GET", body=None, token=None, expected=200, extra=None):
        headers = dict(extra or {})
        if token:
            headers["Authorization"] = "Bearer " + token
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        started = time.perf_counter()
        req = urllib.request.Request(
            origin + path, data=data, headers=headers, method=method
        )
        try:
            response = urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            assert response.status == expected, (path, response.status, expected)
            raw = response.read()
            assert response.headers.get("cache-control") == "no-store"
        latencies.append(
            {"path": path, "seconds": round(time.perf_counter() - started, 3)}
        )
        return json.loads(raw) if raw else {}

    request("/health")
    assert len(request("/public/examples")["runs"]) == 3
    request("/v1/sessions", "POST", {}, expected=401)
    request(
        "/demo/access",
        "POST",
        extra={"Origin": "https://untrusted.example"},
        expected=403,
    )
    a = request("/demo/access", "POST", expected=201)["token"]
    b = request("/demo/access", "POST", expected=201)["token"]
    first = request("/v1/sessions", "POST", {"forecast_mode": "experimental"}, a, 201)
    second = request("/v1/sessions", "POST", {}, b, 201)
    sid = first["session_id"]
    request("/admin/status", token=a, expected=403)
    request(f"/v1/sessions/{sid}", token=b, expected=404)
    request(f"/v1/sessions/{sid}", "DELETE", token=b, expected=404)
    mission = {
        "command_id": "container-mission",
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
        {"command_id": "container-advance", "expected_revision": 1, "target_s": 300},
        a,
    )
    assert advanced["observed_s"] == 300 and advanced["revision"] == 2
    assert advanced["missions"][0]["lines"][0]["minimum"] == 8
    request(
        f"/v1/sessions/{sid}/advance",
        "POST",
        {"command_id": "too-long", "expected_revision": 2, "target_s": 601},
        a,
        422,
    )
    request(
        f"/v1/sessions/{sid}/advance",
        "POST",
        {"command_id": "stale", "expected_revision": 0, "target_s": 600},
        a,
        409,
    )
    # Controlled fault injection in the disposable test database: exercise the
    # real process-kill path with 1 ms, without waiting for the default 20 s.
    fault = internal(
        """
import json,sys
from dataclasses import replace
from pathlib import Path
from fastapi import HTTPException
from src.api.demo_store import DemoPolicy,DemoStore
from src.api.logistics import Advance
data=json.load(sys.stdin)
secret=Path('/app/runtime/demo-admin.key').read_text().strip()
store=DemoStore('/app/runtime/demo.sqlite3',secret,
    policy=replace(DemoPolicy(),worker_timeout_s=.001))
def workers():
    total=0
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                args=(p/'cmdline').read_bytes().split(bytes([0]))
                total+=b'src.api.demo_worker' in args
            except OSError:pass
    return total
before=workers()
try:
    store.command(data['token'],data['sid'],'advance',
        Advance(command_id='timeout',expected_revision=2,target_s=600))
    result={'status':200}
except HTTPException as exc:
    result={'status':exc.status_code,'detail':exc.detail}
result.update(workers_before=before,workers_after=workers())
print(json.dumps(result))
""",
        {"token": a, "sid": sid},
    )
    assert (
        fault["status"] == 503
        and fault["workers_before"] == fault["workers_after"] == 0
    )
    assert request(f"/v1/sessions/{sid}", token=a) == advanced
    # Recreate the container, not only the process. Only its named volume persists.
    command(
        compose
        + [
            "up",
            "-d",
            "--force-recreate",
            "--no-build",
            "--wait",
            "--wait-timeout",
            "90",
        ]
    )
    old_cid = cid
    cid = command(compose + ["ps", "-q", "demo"])
    assert cid != old_cid
    after = json.loads(command(["docker", "inspect", cid]))[0]
    assert (
        next(m["Name"] for m in after["Mounts"] if m["Destination"] == "/app/runtime")
        == volume
    )
    assert request(f"/v1/sessions/{sid}", token=a) == advanced
    assert request(f"/v1/sessions/{sid}/missions", "POST", mission, a) == created
    request(
        f"/v1/sessions/{sid}/missions", "POST", {**mission, "deadline_s": 1300}, a, 409
    )
    assert request(f"/v1/sessions/{sid}", token=a) == advanced
    request("/demo/access", "DELETE", token=a, expected=204)
    request(f"/v1/sessions/{sid}", token=a, expected=401)
    assert request(f"/v1/sessions/{second['session_id']}", token=b) == second
    # Advance only the test lease's expiry in SQLite; do not change host time.
    expired = internal(
        """
import json,sqlite3,sys
data=json.load(sys.stdin)
with sqlite3.connect('/app/runtime/demo.sqlite3') as db:
    cursor=db.execute('UPDATE leases SET expires=0 WHERE token='
        '(SELECT owner FROM sessions WHERE sid=?)',(data['sid'],))
    print(json.dumps({'expired_test_leases':cursor.rowcount}))
""",
        {"sid": second["session_id"]},
    )
    assert expired["expired_test_leases"] == 1
    request(f"/v1/sessions/{second['session_id']}", token=b, expected=401)
    state = admin()
    assert state["sessions"] == state["leases"] == 0
    tables = internal("""
import json,sqlite3
with sqlite3.connect('/app/runtime/demo.sqlite3') as db:
    print(json.dumps({name:db.execute('SELECT count(*) FROM '+name).fetchone()[0]
        for name in ['leases','sessions','commands']}))
""")
    assert all(count == 0 for count in tables.values())
    return {
        "passed": True,
        "container_id": cid,
        "image_id": after["Image"],
        "base_digest": (
            "sha256:" "a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1"
        ),
        "platform": "linux/amd64",
        "environment": environment,
        "validated_source_sha256": source_hashes,
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "pip_check": pip_check,
        "loopback_port": port,
        "read_only_rootfs": True,
        "memory_limit_bytes": host["Memory"],
        "cpu_limit": 1,
        "pids_limit": 64,
        "capabilities_dropped": host["CapDrop"],
        "no_new_privileges": True,
        "healthy": True,
        "container_recreated": True,
        "persistent_volume_verified": True,
        "durable_retry": True,
        "ownership_verified": True,
        "timeout_fault_injection": fault,
        "expired_test_lease_purged": True,
        "final_table_counts": tables,
        "latencies": latencies,
        "active_model": None,
        "public_deployment_verified": False,
        "hosting_created": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not args.project.startswith("logistics-r02-check"):
        parser.error("use a disposable logistics-r02-check project")
    result = verify(args.project, args.port)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(
        json.dumps(
            {
                "passed": True,
                "http_checks": len(result["latencies"]),
                "container_recreated": True,
                "session_tables_empty": True,
            }
        )
    )


if __name__ == "__main__":
    main()
