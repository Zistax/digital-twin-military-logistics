"""Schedule observable forecasts without changing the frozen D03 generator."""

from copy import deepcopy
import json

from .rolling import rolling_observations


class ForecastSession:
    """Flush after each observed command batch; repeated clocks upsert one row."""

    def __init__(self, model, model_sha256, interval_s=1800, session_id="m02"):
        if type(interval_s) is not int or interval_s <= 0:
            raise ValueError("positive forecast interval required")
        if len(model_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in model_sha256
        ):
            raise ValueError("model SHA256 required")
        self.model, self.model_sha256 = model, model_sha256
        self.interval_s, self.session_id = interval_s, session_id
        self.creations, self.due, self.signatures = {}, {}, {}
        self.records, self.positions, self.stopped = [], {}, set()
        self.counter = 0

    def _record(self, record):
        key = record["prediction_id"]
        value = deepcopy(record)
        value["model_sha256"] = self.model_sha256
        if key in self.positions:
            previous = self.records[self.positions[key]]
            if "trigger_reasons" in previous and "trigger_reasons" in value:
                value["trigger_reasons"] = sorted(
                    set(previous["trigger_reasons"] + value["trigger_reasons"])
                )
            self.records[self.positions[key]] = value
        else:
            self.positions[key] = len(self.records)
            self.records.append(value)
        return deepcopy(value)

    def register(self, creation):
        mid = creation["mission_id"]
        if mid in self.creations:
            if self.creations[mid] != creation:
                raise ValueError("conflicting creation")
            return None
        self.creations[mid] = deepcopy(creation)
        self.due[mid] = creation["observed_s"] + self.interval_s
        result = self.model.predict_creation(creation)
        result.update(
            prediction_id=f"{creation['simulation_id']}:{mid}:creation",
            observed_s=creation["observed_s"],
            snapshot=deepcopy(creation),
            trigger_reasons=["creation"],
        )
        return self._record(result)

    def flush(self, warehouse, observed_events=()):
        state = warehouse.snapshot()
        now = state["clock"]
        live = {o["mission_id"]: o for o in rolling_observations(warehouse)}
        emitted = []
        for mid, creation in self.creations.items():
            if mid in self.stopped or now < creation["observed_s"]:
                continue
            if mid not in state["jobs"]:
                raise ValueError("register mission in warehouse before flushing")
            key = f"{creation['simulation_id']}:{mid}:rolling:{now}"
            if mid not in live:
                outcome = warehouse.outcome(mid, now)
                reason = (
                    "cancelled" if outcome.status == "cancelled" else "quota_reached"
                )
                self.stopped.add(mid)
                emitted.append(
                    self._record(
                        {
                            "prediction_id": key,
                            "observed_s": now,
                            "model_version": "m02-v1",
                            "status": "stopped",
                            "reasons": [reason],
                        }
                    )
                )
                continue
            observation = live[mid]
            fields = observation["features"]
            signature = json.dumps(
                {
                    k: v
                    for k, v in fields.items()
                    if k not in {"elapsed_s", "seconds_to_deadline"}
                },
                sort_keys=True,
            )
            triggers = list(observed_events)
            if self.signatures.get(mid) != signature:
                triggers.append("observable_state_changed")
            if now >= self.due[mid]:
                triggers.append("periodic")
                while self.due[mid] <= now:
                    self.due[mid] += self.interval_s
            if now == creation["features"]["deadline_s"]:
                triggers.append("deadline")
            self.signatures[mid] = signature
            if not triggers:
                continue
            result = self.model.predict(creation, observation)
            result.update(
                prediction_id=key,
                observed_s=now,
                snapshot=observation,
                creation_snapshot=creation,
                trigger_reasons=sorted(set(triggers)),
            )
            emitted.append(self._record(result))
        return emitted

    def advance_to(self, warehouse, target_s):
        now = warehouse.snapshot()["clock"]
        if type(target_s) is not int or target_s < now:
            raise ValueError("monotonic integer target required")
        output = self.flush(warehouse)
        while now < target_s:
            stops = [target_s, now + warehouse.tick_s]
            for mid, creation in self.creations.items():
                if mid in self.stopped:
                    continue
                deadline = creation["features"]["deadline_s"]
                stops.extend(t for t in (deadline, self.due[mid]) if t > now)
            now = min(stops)
            self.counter += 1
            warehouse.advance(f"{self.session_id}:step:{self.counter}", now)
            output.extend(self.flush(warehouse))
        return output
