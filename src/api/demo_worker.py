"""Bounded, disposable process for deterministic native session replay."""

import json
import sys

from fastapi import HTTPException

from src.api.logistics import (
    Advance,
    Cancel,
    Decision,
    NewMission,
    NewSession,
    Session,
    SessionStore,
    ROOT,
)

COMMANDS = {
    "advance": Advance,
    "mission": NewMission,
    "decision": Decision,
    "cancel": Cancel,
}


def replay(payload):
    session = Session(NewSession.model_validate(payload["config"]), ROOT)
    session.id = payload["sid"]
    session.w.simulation_id = "interactive-" + session.id
    store = SessionStore()
    store.sessions[session.id] = session
    view = session.view()
    for item in payload["journal"]:
        view = store.command(
            session.id,
            item["operation"],
            COMMANDS[item["operation"]].model_validate(item["body"]),
        )
    return view


def main():
    try:
        payload = json.loads(sys.stdin.read(262145))
        result = {"view": replay(payload)}
    except HTTPException as exc:
        result = {"status": exc.status_code, "detail": exc.detail}
    except Exception:
        # Internal diagnostics must not reveal paths or latent simulator state.
        result = {"status": 503, "detail": "simulation unavailable"}
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
