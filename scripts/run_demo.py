"""Run the restricted R02 demo offline, or behind a separately configured TLS proxy."""

import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--listen", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1"
    )
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    runtime = ROOT / "runtime"
    runtime.mkdir(exist_ok=True)
    key = runtime / "demo-admin.key"
    if not os.environ.get("DEMO_ADMIN_SECRET"):
        if not key.exists():
            fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as target:
                target.write(secrets.token_urlsafe(48))
        os.environ["DEMO_ADMIN_SECRET"] = key.read_text().strip()
    origin = os.environ.setdefault(
        "DEMO_PUBLIC_ORIGIN", f"http://127.0.0.1:{args.port}"
    )
    if args.status or args.cleanup:
        endpoint = "/admin/cleanup" if args.cleanup else "/admin/status"
        req = urllib.request.Request(
            origin + endpoint,
            method="POST" if args.cleanup else "GET",
            headers={"Authorization": "Bearer " + os.environ["DEMO_ADMIN_SECRET"]},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            print(response.read().decode())
        return
    print(f"Demo: {origin} · loopback default · Ctrl+C to stop", flush=True)
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.api.demo_app:create_demo_app",
        "--factory",
        "--host",
        args.listen,
        "--port",
        str(args.port),
        "--workers",
        "1",
        "--limit-concurrency",
        "8",
        "--backlog",
        "16",
        "--timeout-keep-alive",
        "5",
        "--no-access-log",
        "--no-proxy-headers",
    ]
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
