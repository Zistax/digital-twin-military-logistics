"""Restricted demonstration entry point, separate from the complete local API."""

import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict
import hmac
import json
import os
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.api.demo_store import DemoStore
from src.api.logistics import (
    Advance,
    Cancel,
    Decision,
    NewMission,
    NewSession,
    ROOT,
    catalog,
    model_quality,
)

STATIC = ROOT / "src/ui/demo"


def create_demo_app(database=None, admin_secret=None, origin=None, policy=None):
    secret = admin_secret or os.environ.get("DEMO_ADMIN_SECRET", "")
    public_origin = (
        origin or os.environ.get("DEMO_PUBLIC_ORIGIN", "http://127.0.0.1:8080")
    ).rstrip("/")
    parsed = urlsplit(public_origin)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username
    ):
        raise ValueError("configure a single absolute origin")
    if parsed.scheme != "https" and parsed.hostname not in (
        "localhost",
        "127.0.0.1",
        "testserver",
    ):
        raise ValueError("public deployments require HTTPS")
    store = DemoStore(
        database or os.environ.get("DEMO_DATABASE", "runtime/demo.sqlite3"),
        secret,
        policy=policy,
    )

    @asynccontextmanager
    async def lifespan(app):
        async def cleanup():
            while True:
                await asyncio.sleep(30)
                with suppress(HTTPException):
                    await run_in_threadpool(store.maintenance)

        task = asyncio.create_task(cleanup())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(
        title="Demo sintetica limitata",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.store = store
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=[parsed.hostname, "127.0.0.1", "localhost"]
    )

    @app.middleware("http")
    async def boundaries(request, call_next):
        try:
            if request.headers.get("origin") not in (None, public_origin):
                raise HTTPException(403, "origin not permitted")
            body = bytearray()
            async with asyncio.timeout(5):
                async for part in request.stream():
                    body.extend(part)
                    if len(body) > 8192:
                        raise HTTPException(413, "request body too large")
            request._body = bytes(body)
            if request.url.path.startswith(("/v1", "/demo", "/admin", "/public")):
                await run_in_threadpool(
                    store.throttle,
                    request.client.host if request.client else "unknown",
                    request.url.path == "/demo/access",
                )
            response = await call_next(request)
        except TimeoutError:
            response = JSONResponse(
                {"detail": "request body timed out"}, status_code=408
            )
        except HTTPException as exc:
            response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            if exc.status_code == 429:
                response.headers["Retry-After"] = "60"
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": (
                    "default-src 'self'; script-src 'self'; style-src 'self'; "
                    "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
                    "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
                ),
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            }
        )
        if parsed.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    def bearer(request: Request):
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer ") or len(header) > 256:
            raise HTTPException(401, "bearer access required")
        return header[7:]

    def admin(token=Depends(bearer)):
        if not hmac.compare_digest(token.encode(), secret.encode()):
            raise HTTPException(403, "administrator access required")

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "restricted-demo"}

    @app.get("/")
    def home():
        return FileResponse(STATIC / "index.html")

    @app.get("/assets/{name}")
    def assets(name: str):
        if name not in ("demo.js", "demo.css"):
            raise HTTPException(404)
        return FileResponse(STATIC / name)

    @app.get("/public/policy")
    def limits():
        return {
            "limits": asdict(store.policy),
            "active_model": None,
            "experimental_only": True,
            "persistence": "sqlite command journal",
            "retention": "fixed expiry; cleanup every 30 seconds while running",
            "online_published": False,
        }

    @app.get("/public/examples")
    def examples():
        summary = json.loads((ROOT / "reports/r01-v1/pilot-summary.json").read_text())
        return {
            "source": "R01 exploratory pilot, seed 3; not ML validation",
            "all_valid": summary["all_valid"],
            "runs": [
                {k: r[k] for k in ("profile", "kpi") if k in r} for r in summary["runs"]
            ],
            "limitations": summary["limitations"],
        }

    @app.post("/demo/access", status_code=201)
    def access():
        return store.access()

    @app.delete("/demo/access", status_code=204)
    def revoke(token=Depends(bearer)):
        store.revoke(token)
        return Response(status_code=204)

    @app.get("/v1/catalog")
    def get_catalog():
        return catalog()

    @app.get("/v1/model-quality")
    def quality():
        return model_quality()

    @app.post("/v1/sessions", status_code=201)
    def create(body: NewSession, token=Depends(bearer)):
        if (
            body.seed != 0
            or body.profile != "regular"
            or body.forecast_mode == "approved"
        ):
            raise HTTPException(
                422, "online preset: seed 0, regular, off/experimental only"
            )
        return store.create(token, body)

    @app.get("/v1/sessions/{sid}")
    def read(sid: str, token=Depends(bearer)):
        return store.read(token, sid)

    @app.delete("/v1/sessions/{sid}", status_code=204)
    def delete(sid: str, token=Depends(bearer)):
        store.delete(token, sid)
        return Response(status_code=204)

    @app.post("/v1/sessions/{sid}/advance")
    def advance(sid: str, body: Advance, token=Depends(bearer)):
        return store.command(token, sid, "advance", body)

    @app.post("/v1/sessions/{sid}/missions")
    def mission(sid: str, body: NewMission, token=Depends(bearer)):
        return store.command(token, sid, "mission", body)

    @app.post("/v1/sessions/{sid}/decisions")
    def decision(sid: str, body: Decision, token=Depends(bearer)):
        return store.command(token, sid, "decision", body)

    @app.post("/v1/sessions/{sid}/cancellations")
    def cancel(sid: str, body: Cancel, token=Depends(bearer)):
        return store.command(token, sid, "cancel", body)

    @app.get("/admin/status", dependencies=[Depends(admin)])
    def status():
        return {
            **store.maintenance(),
            "policy": asdict(store.policy),
            "model_mutations": "offline only",
        }

    @app.post("/admin/cleanup", dependencies=[Depends(admin)])
    def cleanup():
        return store.maintenance()

    return app
