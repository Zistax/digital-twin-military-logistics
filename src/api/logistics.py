"""Native local sessions. Public projections never serialize latent simulator state."""

from copy import deepcopy
from dataclasses import asdict, replace
from decimal import Decimal
import json
from pathlib import Path
from threading import RLock
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response
import joblib
from pydantic import BaseModel, ConfigDict, Field

from src.logistics.core import Mission, MissionLine
from src.logistics.dataset import creation_observation
from src.logistics.estimates import (
    InitialEstimate,
    estimate_request,
    mission_from_estimate,
)
from src.logistics.forecast_session import ForecastSession
from src.logistics.model_registry import active_artifact, safe_path, verify_version
from src.logistics.scenarios import (
    DEPOTS,
    THRESHOLDS,
    ScenarioConfig,
    ScenarioRequest,
    generate_requests,
    initialize_scenario,
    reference_catalog,
)

ROOT = Path(__file__).resolve().parents[2]
router = APIRouter(prefix="/v1", tags=["Logistica nativa"])
LIMITATIONS = [
    "Demo sintetica: nessun modello attivo nel registro M03.",
    "49 gate M03 falliti; durate con errori elevati e intervalli molto ampi.",
    "Durata condizionata alla quota; le missioni censurate non hanno durata zero.",
    "Copertura statistica non validata per ogni aggiornamento a 30 minuti/eventi.",
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class NewSession(Input):
    seed: int = Field(default=0, ge=0, le=3)
    profile: Literal["regular", "pressure", "perturbed"] = "regular"
    forecast_mode: Literal["off", "experimental", "approved"] = "off"


class Command(Input):
    command_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    expected_revision: int = Field(ge=0)


class Advance(Command):
    target_s: int = Field(ge=0, le=172800)


class NewMission(Command):
    origin_id: str = Field(min_length=1, max_length=80)
    destination_id: str = Field(min_length=1, max_length=80)
    quantities: dict[str, Annotated[int, Field(gt=0, le=1000)]] = Field(
        min_length=1, max_length=15
    )
    deadline_s: int = Field(gt=0, le=259200)
    urgent: bool = False


class Decision(Command):
    request_id: str = Field(min_length=1, max_length=80)
    decision: Literal["approve", "defer", "reject"]


class Cancel(Command):
    mission_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)


def reject(status, field, reason):
    raise HTTPException(status, detail={"field": field, "reason": reason})


def load_forecaster(mode, root):
    if mode == "off":
        return None
    try:
        registry = json.loads((root / "models/registry-v1.json").read_text())
        if mode == "approved":
            if registry["active"] is None:
                reject(409, "forecast_mode", "no approved active model")
            version = registry["active"]
            artifact = active_artifact(registry, root)
        else:
            version = "m02-v1"
            entry = verify_version(registry, version, root)
            artifact = safe_path(root, entry["artifact"]["path"])
        entry = verify_version(
            registry, version, root, require_eligible=mode == "approved"
        )
        model = joblib.load(artifact)
        if not callable(getattr(model, "predict_creation", None)):
            reject(409, "forecast_mode", "rolling pipeline required")
        return ForecastSession(model, entry["artifact"]["sha256"])
    except (OSError, ValueError, KeyError) as exc:
        reject(503, "forecast_mode", f"model evidence unavailable: {exc}")


class Session:
    def __init__(self, body, root):
        self.config = ScenarioConfig(body.seed, body.profile, 1, 1)
        self.forecast = load_forecaster(body.forecast_mode, root)
        self.mode = body.forecast_mode
        self.w, _ = initialize_scenario(self.config)
        self.id = uuid4().hex
        self.w.simulation_id = "interactive-" + self.id
        self.w._policy = replace(self.w._policy, auto_approve=False)
        self.planned = tuple(generate_requests(self.config))
        self.cursor, self.revision, self.invalid = 0, 0, False
        self.creations, self.commands = {}, {}

    def flush(self, events=()):
        if self.forecast:
            self.forecast.flush(self.w, events)

    def step(self, target):
        if self.forecast:
            self.forecast.advance_to(self.w, target)
        else:
            self.w.advance(f"ui:step:{len(self.w._commands)}", target)

    def admit(self, request, deadline=None):
        w = self.w
        estimate = estimate_request(w, request)
        basis, source = estimate, "observable_estimate"
        if estimate.duration_s is None:
            basis = InitialEstimate(w._clock, 86400, None)
            source = "configured_allowance"
        mission = mission_from_estimate(w.simulation_id, request, basis)
        if deadline is not None:
            mission = replace(mission, deadline_s=deadline)
            source = "manual"
        creation = creation_observation(w, request, mission, estimate, source)
        w.register(
            f"ui:register:{mission.mission_id}", w._clock, mission, request.urgent
        )
        w.schedule(f"ui:schedule:{mission.mission_id}", w._clock, mission.mission_id)
        self.creations[mission.mission_id] = creation
        if self.forecast:
            self.forecast.register(creation)

    def advance(self, target):
        while (
            self.cursor < len(self.planned)
            and self.planned[self.cursor].start_s <= target
        ):
            at = self.planned[self.cursor].start_s
            self.step(at)
            while (
                self.cursor < len(self.planned)
                and self.planned[self.cursor].start_s == at
            ):
                self.admit(self.planned[self.cursor])
                self.cursor += 1
            self.w.advance(f"ui:dispatch:{at}", at)
            self.flush()
        self.step(target)

    def validate(self, operation, body):
        w = self.w
        if operation == "advance":
            if not w._clock < body.target_s <= min(w._clock + 3600, self.config.stop_s):
                reject(422, "target_s", "advance 1..3600 seconds within 48 hours")
        elif operation == "mission":
            if len(w._jobs) >= 200:
                reject(429, "missions", "mission limit reached")
            if w._clock >= self.config.stop_s:
                reject(409, "session", "scenario horizon reached")
            for field in ("origin_id", "destination_id"):
                try:
                    w._validate_depot_items(getattr(body, field), body.quantities)
                except ValueError as exc:
                    reject(422, field, str(exc))
            lines = tuple(
                MissionLine(i, q, THRESHOLDS[i.split("-")[0]])
                for i, q in body.quantities.items()
            )
            try:
                Mission(
                    w.simulation_id,
                    "manual:" + body.command_id,
                    body.origin_id,
                    body.destination_id,
                    w._clock,
                    body.deadline_s,
                    lines,
                )
            except ValueError as exc:
                reject(422, "mission", str(exc))
        elif operation == "decision":
            request = w.observed_incidents()["requests"].get(body.request_id)
            if request is None or request["status"] not in (
                "pending",
                "deferred",
                "rejected",
            ):
                reject(422, "request_id", "unknown or already acted-on request")
        elif operation == "cancel":
            if body.mission_id not in w._jobs:
                reject(422, "mission_id", "unknown mission")
            outcome = w.outcome(body.mission_id, w._clock)
            if (
                not body.reason.strip()
                or outcome.status == "cancelled"
                or outcome.quota_reached_s is not None
            ):
                reject(422, "cancellation", "reason required; mission must be open")

    def mutate(self, operation, body):
        w, now = self.w, self.w._clock
        if operation == "advance":
            self.advance(body.target_s)
            return
        if operation == "mission":
            lines = tuple(
                MissionLine(i, q, THRESHOLDS[i.split("-")[0]])
                for i, q in body.quantities.items()
            )
            request = ScenarioRequest(
                "manual:" + body.command_id,
                now,
                body.origin_id,
                body.destination_id,
                body.urgent,
                lines,
                "manual",
                Decimal(1),
            )
            self.admit(request, body.deadline_s)
        elif operation == "decision":
            w.decide(
                "ui:decision:" + body.command_id, now, body.request_id, body.decision
            )
        else:
            w.cancel("ui:cancel:" + body.command_id, now, body.mission_id, body.reason)
        w.advance("ui:dispatch:" + body.command_id, now)
        self.flush([operation])

    def missions(self):
        w, now = self.w, self.w._clock
        result = []
        for mid, job in w._jobs.items():
            m, outcome = job.mission, w.outcome(mid, now)
            history = (
                [
                    r
                    for r in self.forecast.records
                    if r["prediction_id"].startswith(f"{w.simulation_id}:{mid}:")
                ]
                if self.forecast
                else []
            )
            result.append(
                {
                    "mission_id": mid,
                    "origin_id": m.origin_id,
                    "destination_id": m.destination_id,
                    "start_s": m.start_s,
                    "deadline_s": m.deadline_s,
                    "urgent": job.urgent,
                    "phase": job.status,
                    "waiting_reason": w._allocation_wait.get(mid),
                    "outcome": asdict(outcome),
                    "lines": [
                        {
                            "item_id": line.item_id,
                            "requested": line.requested,
                            "minimum": line.minimum,
                            "accepted": outcome.accepted[line.item_id],
                            "unusable_inspected": outcome.unusable[line.item_id],
                            "reserved": job.reserved.get(line.item_id, 0),
                        }
                        for line in m.lines
                    ],
                    "creation_estimate": self.creations.get(mid),
                    "prediction_history": history,
                    "prediction": (
                        history[-1]
                        if history
                        else {
                            "status": "abstain",
                            "reasons": ["forecast_disabled"],
                            "observed_s": now,
                            "probability_late": None,
                        }
                    ),
                    "explanation": (
                        "Quantità osservate dopo ispezione. "
                        "Le stime possono astenersi; null non significa zero."
                    ),
                }
            )
        return result

    def depots(self):
        w, now = self.w, self.w._clock
        supplies = w.observed_supplies()
        result = []
        for d, store in w._stores.items():
            stock = w._stock[d]
            result.append(
                {
                    "depot_id": d,
                    "stock": stock,
                    "available": {i: w.available(d, i) for i in w._items},
                    "reserved": {
                        i: stock.get(i, 0) - w.available(d, i) for i in w._items
                    },
                    "capacity_m3": {
                        "ordinary": str(store.ordinary_m3),
                        "cold": str(store.cold_m3),
                    },
                    "occupied_m3": {
                        str(cold): str(
                            sum(
                                w._items[i].m3 * q
                                for i, q in stock.items()
                                if w._items[i].cold == cold
                            )
                        )
                        for cold in (False, True)
                    },
                    "quarantine": w._quarantine[d],
                    "berths": w._operations[d].berths,
                    "berths_used": sum(op["depot"] == d for op in w._active.values()),
                    "queue_size": sum(op["depot"] == d for op in w._queue.values()),
                    "opening_now": w._operations[d].calendar.is_open(w._epoch, now),
                    "local_backlog": sum(
                        sum(r["remaining"].values())
                        for r in w._local.values()
                        if r["depot"] == d and r["due_s"] <= now
                    ),
                    "incoming": {
                        sid: s
                        for sid, s in supplies.items()
                        if s["depot"] == d and s["status"] in ("expected", "waiting")
                    },
                }
            )
        return result

    def view(self):
        w, now = self.w, self.w._clock
        missions, depots = self.missions(), self.depots()
        fleet = []
        for v, vehicle in w._vehicles.items():
            movement = w._road.get(v)
            fleet.append(
                {
                    "vehicle_id": v,
                    "position_node": w._positions[v],
                    "assignment": w._busy.get(v),
                    "broken": v in w._broken,
                    "cold": vehicle.cold,
                    "max_kg": str(vehicle.max_kg),
                    "max_m3": str(vehicle.max_m3),
                    "route": (
                        {
                            k: movement[k]
                            for k in ("path", "node", "target", "blocked", "trip_id")
                        }
                        if movement
                        else None
                    ),
                    "loads": [
                        {
                            "trip_id": t,
                            "mission_id": load.mission_id,
                            "quantities": load.quantities,
                            "status": load.status,
                        }
                        for t, load in w._loads.items()
                        if load.vehicle_id == v
                    ],
                }
            )
        reached = [m for m in missions if m["outcome"]["quota_reached_s"] is not None]
        cancelled = sum(m["outcome"]["status"] == "cancelled" for m in missions)
        operations = [
            {
                k: row[k]
                for k in ("trip_id", "kind", "depot", "start_s", "end_s", "overtime_s")
                if k in row
            }
            for row in w._history
            if row.get("end_s", row.get("at_s", 0)) <= now
        ]
        transport = [
            {k: v for k, v in row.items() if k != "end_s"}
            for row in w._transport_log
            if row["at_s"] <= now
        ]
        return deepcopy(
            {
                "schema_version": 1,
                "session_id": self.id,
                "revision": self.revision,
                "valid": not self.invalid,
                "observed_s": now,
                "horizon_s": self.config.stop_s,
                "facts_cutoff_s": now,
                "forecast_mode": self.mode,
                "forecast_label": (
                    "SPERIMENTALE — NON PROMOSSO"
                    if self.mode == "experimental"
                    else (
                        "Solo modello approvato"
                        if self.mode == "approved"
                        else "Previsioni disattivate"
                    )
                ),
                "limitations": LIMITATIONS,
                "missions": missions,
                "depots": depots,
                "fleet": fleet,
                "approvals": w.observed_incidents(),
                "network": {
                    "nodes": [asdict(n) for n in w._network.nodes.values()],
                    "roads": [
                        {**asdict(r), "condition": w._network.conditions[k]}
                        for k, r in w._network.roads.items()
                    ],
                    "environment": w.observed_environment(),
                },
                "analysis": {
                    "missions": len(missions),
                    "quota_reached": len(reached),
                    "cancelled": cancelled,
                    "censored_now": len(missions) - len(reached) - cancelled,
                    "on_time_among_reached": sum(
                        not m["outcome"]["late"] for m in reached
                    ),
                    "busy_fleet_now": sum(v in w._busy for v in w._vehicles),
                    "fleet_total": len(fleet),
                    "observed_wait_seconds": w._wait,
                    "operations_history": operations,
                    "transport_history": transport,
                },
            }
        )


class SessionStore:
    """Single-process local store: serialize mutations and commit detached copies."""

    def __init__(self, root=ROOT, capacity=8):
        self.root, self.capacity = root, capacity
        self.sessions, self.lock = {}, RLock()

    def get(self, sid):
        if sid not in self.sessions:
            reject(404, "session_id", "unknown session")
        return self.sessions[sid]

    def create(self, body):
        with self.lock:
            if len(self.sessions) >= self.capacity:
                reject(429, "sessions", "close a session before creating another")
            session = Session(body, self.root)
            self.sessions[session.id] = session
            return session.view()

    def read(self, sid):
        with self.lock:
            return self.get(sid).view()

    def delete(self, sid):
        with self.lock:
            self.get(sid)
            del self.sessions[sid]

    def command(self, sid, operation, body):
        with self.lock:
            session = self.get(sid)
            key, signature = body.command_id, (operation, body.model_dump())
            if key in session.commands:
                old, response = session.commands[key]
                if old != signature:
                    reject(409, "command_id", "conflicting retry")
                return deepcopy(response)
            if session.invalid:
                reject(409, "session", "invalid simulation; create a new session")
            if body.expected_revision != session.revision:
                reject(409, "expected_revision", "stale view; refresh before sending")
            session.validate(operation, body)
            memo = {id(session.commands): session.commands}
            if session.forecast:
                memo[id(session.forecast.model)] = session.forecast.model
            candidate = deepcopy(session, memo)
            candidate.commands = dict(session.commands)
            try:
                candidate.mutate(operation, body)
            except (ValueError, RuntimeError) as exc:
                session.invalid = True
                reject(409, "simulation", f"invariant failure; session stopped: {exc}")
            candidate.revision += 1
            response = candidate.view()
            candidate.commands[key] = (signature, deepcopy(response))
            if len(candidate.commands) > 16:
                del candidate.commands[next(iter(candidate.commands))]
            self.sessions[sid] = candidate
            return response


store = SessionStore()


@router.get("/catalog")
def catalog():
    return {
        "depots": DEPOTS,
        "items": [asdict(i) for i in reference_catalog()],
        "quota_thresholds": THRESHOLDS,
    }


@router.get("/model-quality")
def model_quality():
    registry = json.loads((ROOT / "models/registry-v1.json").read_text())
    return {
        "active": registry["active"],
        "versions": {
            v: {"status": e["status"], "sha256": e["artifact"]["sha256"]}
            for v, e in registry["versions"].items()
        },
        "evaluation": json.loads((ROOT / "reports/m03-v1/report.json").read_text()),
    }


@router.post("/sessions", status_code=201)
def create_session(body: NewSession):
    return store.create(body)


@router.get("/sessions/{sid}")
def read_session(sid: str):
    return store.read(sid)


@router.delete("/sessions/{sid}", status_code=204)
def delete_session(sid: str):
    store.delete(sid)
    return Response(status_code=204)


@router.post("/sessions/{sid}/advance")
def advance_session(sid: str, body: Advance):
    return store.command(sid, "advance", body)


@router.post("/sessions/{sid}/missions")
def create_mission(sid: str, body: NewMission):
    return store.command(sid, "mission", body)


@router.post("/sessions/{sid}/decisions")
def decide(sid: str, body: Decision):
    return store.command(sid, "decision", body)


@router.post("/sessions/{sid}/cancellations")
def cancel(sid: str, body: Cancel):
    return store.command(sid, "cancel", body)
