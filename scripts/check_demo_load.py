"""Bounded local eight-visitor/periodic-cleanup test on an empty Docker project."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from threading import Barrier, Lock
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
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
            timeout=90,
        )
        return result.stdout.strip()

    cid = command(compose + ["ps", "-q", "demo"])
    if not cid or "\n" in cid:
        raise ValueError("one running disposable load-test container required")
    inspection = json.loads(command(["docker", "inspect", cid]))[0]
    assert inspection["HostConfig"]["PortBindings"] == {
        "8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(port)}]
    }

    def internal(code, payload=None):
        return json.loads(
            command(
                ["docker", "exec", "-i", cid, "python", "-c", code],
                json.dumps(payload) if payload is not None else None,
            )
        )

    counts_code = """
import json,sqlite3
with sqlite3.connect('/app/runtime/demo.sqlite3') as db:
    print(json.dumps({name:db.execute('SELECT count(*) FROM '+name).fetchone()[0]
        for name in ['leases','sessions','commands']}))
"""
    assert all(
        v == 0 for v in internal(counts_code).values()
    ), "empty test runtime required"
    runtime = internal("""
import hashlib,json,sys
from pathlib import Path
limit=None
for p in Path('/proc').iterdir():
    if p.name.isdigit():
        try:args=(p/'cmdline').read_bytes().split(bytes([0]))
        except OSError:continue
        if b'uvicorn' in args and b'--limit-concurrency' in args:
            limit=int(args[args.index(b'--limit-concurrency')+1])
print(json.dumps({'python':sys.version,'http_concurrency_limit':limit,
    'launcher_sha256':hashlib.sha256(Path('scripts/run_demo.py').read_bytes()).hexdigest()}))
""")
    origin = f"http://127.0.0.1:{port}"
    timings = []
    timing_lock = Lock()

    def request(path, method="GET", body=None, token=None):
        headers = {}
        if token:
            headers["Authorization"] = "Bearer " + token
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            origin + path, data=data, headers=headers, method=method
        )
        started = time.perf_counter()
        try:
            response = urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            status = response.status
            raw = response.read()
        seconds = time.perf_counter() - started
        route = "/v1/sessions/:id" if path.startswith("/v1/sessions/") else path
        with timing_lock:
            timings.append(
                {"route": route, "status": status, "seconds": round(seconds, 4)}
            )
        try:
            result = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            result = {"detail": "non-JSON admission response"}
        return status, result, seconds

    visitors = []
    for index in range(9):
        if index == 5:
            delay = 61 - (time.time() % 60)
            print(
                json.dumps(
                    {"phase": "public_token_budget", "wait_seconds": round(delay, 1)}
                ),
                flush=True,
            )
            time.sleep(delay)
        status, access, _ = request("/demo/access", "POST")
        assert status == 201, ("token issuance", status)
        token = access["token"]
        if index < 8:
            body = {"forecast_mode": "experimental" if index == 0 else "off"}
            status, view, _ = request("/v1/sessions", "POST", body, token)
            assert status == 201, ("session creation", status)
            visitors.append({"token": token, "sid": view["session_id"], "revision": 0})
        else:
            extra_token = token
    print(json.dumps({"phase": "eight_sessions_ready"}), flush=True)
    status, capacity, _ = request("/v1/sessions", "POST", {}, extra_token)
    capacity_ok = (
        status == 429 and capacity.get("detail") == "demo session capacity reached"
    )
    assert len({v["sid"] for v in visitors}) == 8

    def burst(action):
        barrier = Barrier(8)

        def run(index):
            barrier.wait(timeout=10)
            return action(index, visitors[index])

        with ThreadPoolExecutor(max_workers=8) as pool:
            return list(pool.map(run, range(8)))

    reads = []
    for _ in range(2):
        reads.extend(
            burst(
                lambda i, v: (i, *request(f"/v1/sessions/{v['sid']}", token=v["token"]))
            )
        )
    idle_identity_ok = all(
        status != 200 or body.get("session_id") == visitors[i]["sid"]
        for i, status, body, _ in reads
    )
    idle_all_accepted = all(status == 200 for _, status, _, _ in reads)
    successful_times = sorted(
        seconds for _, status, _, seconds in reads if status == 200
    )
    p95 = (
        successful_times[math.ceil(0.95 * len(successful_times)) - 1]
        if successful_times
        else None
    )
    crossing = []
    for index, v in enumerate(visitors):
        status, _, _ = request(
            f"/v1/sessions/{visitors[(index+1)%8]['sid']}", token=v["token"]
        )
        crossing.append(status)

    monitor_code = """
import json,time
from pathlib import Path
maximum=0
deadline=time.monotonic()+8
while time.monotonic()<deadline:
    count=0
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                args=(p/'cmdline').read_bytes().split(bytes([0]))
                count+=b'src.api.demo_worker' in args
            except OSError:pass
    maximum=max(maximum,count)
    time.sleep(.02)
print(json.dumps({'max_workers_observed':maximum}))
"""
    monitor = subprocess.Popen(
        ["docker", "exec", cid, "python", "-c", monitor_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        time.sleep(0.2)
        mutations = burst(
            lambda i, v: (
                i,
                *request(
                    f"/v1/sessions/{v['sid']}/advance",
                    "POST",
                    {
                        "command_id": f"load-{i}",
                        "expected_revision": 0,
                        "target_s": 300,
                    },
                    v["token"],
                ),
            )
        )
        monitored, _ = monitor.communicate(timeout=20)
        assert monitor.returncode == 0
        max_workers = json.loads(monitored)["max_workers_observed"]
    finally:
        if monitor.poll() is None:
            monitor.kill()
            monitor.communicate()
    mutation_identity_ok = all(
        status != 200 or body.get("session_id") == visitors[i]["sid"]
        for i, status, body, _ in mutations
    )
    mutation_statuses_ok = all(status in (200, 503) for _, status, _, _ in mutations)
    state_consistent = True
    committed = []
    for i, v in enumerate(visitors):
        status, current, _ = request(f"/v1/sessions/{v['sid']}", token=v["token"])
        mutation_status = mutations[i][1]
        expected = 1 if mutation_status == 200 else 0
        state_consistent &= status == 200 and current.get("revision") == expected
        if status == 200:
            v["revision"] = current["revision"]
        if expected:
            committed.append(i)
    keeper = committed[0] if committed else 0
    for index, v in enumerate(visitors):
        if index != keeper:
            assert request("/demo/access", "DELETE", token=v["token"])[0] == 204
    assert request("/demo/access", "DELETE", token=extra_token)[0] == 204
    before_expiry = internal(counts_code)
    assert before_expiry["leases"] == before_expiry["sessions"] == 1
    expired = internal(
        """
import json,sqlite3,sys,time
data=json.load(sys.stdin);expires=time.time()+2
with sqlite3.connect('/app/runtime/demo.sqlite3') as db:
    row=db.execute('UPDATE leases SET expires=? WHERE token='
        '(SELECT owner FROM sessions WHERE sid=?)',(expires,data['sid']))
    assert row.rowcount==1
print(json.dumps({'expires_at':expires}))
""",
        {"sid": visitors[keeper]["sid"]},
    )
    print(
        json.dumps({"phase": "waiting_for_periodic_cleanup", "no_api_requests": True}),
        flush=True,
    )
    deadline = time.monotonic() + 37
    final_counts = before_expiry
    while time.monotonic() < deadline:
        final_counts = internal(counts_code)
        if all(value == 0 for value in final_counts.values()):
            break
        time.sleep(1)
    purged = all(value == 0 for value in final_counts.values())
    observed_delay = max(0, time.time() - expired["expires_at"])
    if not purged:
        # Leave no live test access behind if the scheduler is broken.
        request("/demo/access", "DELETE", token=visitors[keeper]["token"])
    expired_status = request(
        f"/v1/sessions/{visitors[keeper]['sid']}", token=visitors[keeper]["token"]
    )[0]
    passed = all(
        [
            capacity_ok,
            idle_all_accepted,
            idle_identity_ok,
            p95 is not None and p95 < 1,
            all(s == 404 for s in crossing),
            mutation_statuses_ok,
            mutation_identity_ok,
            state_consistent,
            max_workers == 1,
            purged,
            expired_status == 401,
        ]
    )
    return {
        "passed": passed,
        "scope": "local Linux Docker, eight visitors from one source IP",
        "image_id": inspection["Image"],
        "runtime": runtime,
        "visitors": 8,
        "idle_read_samples": len(reads),
        "idle_statuses": [s for _, s, _, _ in reads],
        "idle_all_accepted": idle_all_accepted,
        "idle_read_p95_seconds": round(p95, 4) if p95 is not None else None,
        "idle_read_p95_target_seconds": 1,
        "no_cross_owner_data": idle_identity_ok and mutation_identity_ok,
        "cross_owner_rejected": all(s == 404 for s in crossing),
        "ninth_session_rejected": capacity_ok,
        "mutation_statuses": [s for _, s, _, _ in mutations],
        "successful_mutations": sum(s == 200 for _, s, _, _ in mutations),
        "mutation_backpressure_statuses_ok": mutation_statuses_ok,
        "committed_state_consistent": state_consistent,
        "max_workers_observed": max_workers,
        "periodic_purge_without_api_requests": purged,
        "before_periodic_purge": before_expiry,
        "final_table_counts": final_counts,
        "observed_purge_delay_after_forced_expiry_s": round(observed_delay, 3),
        "default_30_minute_lifetime_waited": False,
        "expiry_fault_injection": "only one synthetic lease set to now+2 s",
        "request_count": len(timings),
        "timings": timings,
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "public_deployment_verified": False,
        "hosting_created": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="logistics-r02-check-load")
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not args.project.startswith("logistics-r02-check-load"):
        parser.error("use a dedicated logistics-r02-check-load project")
    result = verify(args.project, args.port)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "passed",
                    "idle_statuses",
                    "idle_read_p95_seconds",
                    "mutation_statuses",
                    "max_workers_observed",
                    "periodic_purge_without_api_requests",
                ]
            }
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
