"""Chronological scenario execution with explicit deadline policy and censoring."""

from dataclasses import asdict, dataclass
from itertools import groupby
from datetime import timedelta
from collections import Counter

from .core import natural
from .dataset import creation_observation
from .rolling import rolling_observations
from .cargo_ledger import cargo_events
from .pilot_checks import operational_checkpoint, explain_open_mission
from .journal import Journal
from .provenance import run_manifest
from .context import observation_context
from .estimates import InitialEstimate, estimate_request, mission_from_estimate
from .scenarios import generate_requests, initialize_scenario


@dataclass(frozen=True)
class RunPolicy:
    # A synthetic planning allowance, not a fabricated duration estimate.
    unavailable_allowance_s: int = 86400
    completion_check_s: int = 3600
    observation_interval_s: int = 3600

    def __post_init__(self):
        natural(self.unavailable_allowance_s, "unavailable_allowance_s", True)
        natural(self.completion_check_s, "completion_check_s", True)
        natural(self.observation_interval_s, "observation_interval_s", True)


def run_experiment(
    config, policy=None, *, warehouse=None, requests=None, capture_trace=False
):
    policy = policy or RunPolicy()
    if not isinstance(policy, RunPolicy):
        raise ValueError("RunPolicy required")
    if warehouse is None:
        warehouse, initial = initialize_scenario(config)
    else:
        initial = ()
    w = warehouse
    planned = tuple(generate_requests(config) if requests is None else requests)
    if (
        len({r.request_id for r in planned}) != len(planned)
        or any(not 0 <= r.start_s < config.generation_end_s for r in planned)
        or list(planned) != sorted(planned, key=lambda r: r.start_s)
    ):
        raise ValueError(
            "unique chronological requests inside generation horizon required"
        )
    if w._jobs or w._clock > 0:
        raise ValueError("runner requires a fresh initialized warehouse")
    provenance = run_manifest(w, config, policy)
    w._journal = Journal()
    w._journal.capture(w, 0)
    creation = []
    observations = []
    contexts = []
    rolling = []
    trace = []
    peak_sampled = {"open_missions": 0, "internal_queue": 0, "local_backlog_units": 0}
    next_observation = policy.observation_interval_s

    def advance_to(command_id, target):
        nonlocal next_observation
        while next_observation <= target:
            w.advance(f"runner:observe:{next_observation}", next_observation)
            new_observations = rolling_observations(w)
            rolling.extend(new_observations)
            contexts.extend(observation_context(w, row) for row in new_observations)
            if capture_trace:
                trace.append(operational_checkpoint(w, next_observation))
            peak_sampled["open_missions"] = max(
                peak_sampled["open_missions"],
                sum(job.status != "logistics_complete" for job in w._jobs.values()),
            )
            peak_sampled["internal_queue"] = max(
                peak_sampled["internal_queue"], len(w._queue)
            )
            peak_sampled["local_backlog_units"] = max(
                peak_sampled["local_backlog_units"],
                sum(
                    sum(r["remaining"].values())
                    for r in w._local.values()
                    if r["due_s"] <= next_observation
                ),
            )
            next_observation += policy.observation_interval_s
        w.advance(command_id, target)

    for at_s, batch in groupby(planned, key=lambda r: r.start_s):
        advance_to(f"runner:before:{at_s}", at_s)
        for r in batch:
            estimate = estimate_request(w, r)
            if estimate.duration_s is None:
                # Preserve the original request timestamp and sampled margin.
                basis = InitialEstimate(
                    at_s,
                    policy.unavailable_allowance_s,
                    None,
                    "configured-planning-allowance-v1",
                )
                source = "configured_allowance"
            else:
                basis, source = estimate, "observable_estimate"
            mission = mission_from_estimate(w.simulation_id, r, basis)
            observations.append(creation_observation(w, r, mission, estimate, source))
            contexts.append(observation_context(w, observations[-1]))
            w.register(f"runner:register:{r.request_id}", at_s, mission, r.urgent)
            w.schedule(f"runner:schedule:{r.request_id}", at_s, r.request_id)
            creation.append(
                {
                    "mission_id": r.request_id,
                    "created_s": at_s,
                    "estimate": asdict(estimate),
                    "deadline_source": source,
                    "deadline_basis_s": basis.duration_s,
                    "deadline_margin": r.deadline_margin,
                    "deadline_s": mission.deadline_s,
                }
            )
        w.advance(f"runner:dispatch:{at_s}", at_s)
    advance_to("runner:generation-end", config.generation_end_s)

    def drained(at_s):
        return (
            all(w.outcome(r.request_id, at_s).logistics_complete for r in planned)
            and not w._road
            and not w._pending
            and not w._rescues
            and not w._broken
            and not w._queue
            and not any(op["kind"] != "supply" for op in w._active.values())
        )

    now = config.generation_end_s
    while now < config.stop_s and not drained(now):
        now = min(config.stop_s, now + policy.completion_check_s)
        advance_to(f"runner:drain:{now}", now)
    completed = drained(now)
    outcomes = {}
    for r in planned:
        outcome = w.outcome(r.request_id, now)
        outcomes[r.request_id] = {
            **asdict(outcome),
            "quota_censored": outcome.quota_reached_s is None
            and outcome.status != "cancelled",
            "logistics_open": not outcome.logistics_complete,
        }
    return {
        "config": asdict(config),
        "policy": asdict(policy),
        "stopped_s": now,
        "stop_reason": "missions_drained" if completed else "time_limit",
        "initial_stock": initial,
        "creations": creation,
        "outcomes": outcomes,
        "observations": observations,
        "rolling_observations": rolling,
        "diagnostics": {
            "terminal_blockers": {
                mid: explain_open_mission(w, mid, now)
                for mid in w._jobs
                if outcomes[mid]["logistics_open"]
            },
            "peak_sampled": peak_sampled,
            "mission_statuses": dict(Counter(job.status for job in w._jobs.values())),
            "open_missions": [
                {
                    "mission_id": mid,
                    "status": job.status,
                    "reserved_units": sum(job.reserved.values()),
                    "required_units": sum(line.requested for line in job.mission.lines),
                    "missing_reservation_units": (
                        sum(
                            max(0, line.requested - job.reserved.get(line.item_id, 0))
                            for line in job.mission.lines
                        )
                        if job.status == "waiting"
                        else None
                    ),
                    "trips": dict(
                        Counter(
                            load.status
                            for load in w._loads.values()
                            if load.mission_id == mid
                        )
                    ),
                }
                for mid, job in w._jobs.items()
                if outcomes[mid]["logistics_open"]
            ],
            "wait_seconds": {
                reason: sum(wait[reason] for wait in w._wait.values())
                for reason in ("opening", "stock", "space", "berth")
            },
            "supplies_by_status": dict(
                Counter(s["status"] for s in w._supplies.values())
            ),
            "supply_wait_seconds": {
                reason: sum(wait[reason] for wait in w._supply_wait.values())
                for reason in ("opening", "berth", "space")
            },
            "supply_wait_by_order": w._supply_wait,
            "mission_allocation_wait_seconds": {
                reason: sum(wait.get(reason, 0) for wait in w._mission_wait.values())
                for reason in sorted(
                    {r for waits in w._mission_wait.values() for r in waits}
                )
            },
            "final_allocation_reasons": dict(Counter(w._allocation_wait.values())),
            "local_backlog_units": sum(
                sum(r["remaining"].values())
                for r in w._local.values()
                if r["due_s"] <= now
            ),
            "incident_counts": dict(Counter(a["kind"] for a in w._alerts)),
            "recovery_statuses": dict(
                Counter(r["status"] for r in w._requests.values())
            ),
        },
        "operational_trace": trace,
        "cargo_events": cargo_events(w),
        "run_manifest": provenance,
        "operational_events": w._journal.export(),
        "planning_contexts": contexts,
        "delivery_events": [
            {
                **asdict(event),
                "occurred_utc": (
                    w._epoch + timedelta(seconds=event.occurred_s)
                ).isoformat(),
                "observed_utc": (
                    w._epoch + timedelta(seconds=event.observed_s)
                ).isoformat(),
            }
            for event in w._events
        ],
    }


if __name__ == "__main__":
    import argparse
    import json
    from .scenarios import ScenarioConfig

    parser = argparse.ArgumentParser(
        description="Run a reproducible synthetic logistics scenario"
    )
    parser.add_argument(
        "--profile", choices=("regular", "pressure", "perturbed"), default="regular"
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--extension-days", type=int, default=1)
    parser.add_argument(
        "--dataset-dir", help="new directory for separate creation features and labels"
    )
    args = parser.parse_args()
    result = run_experiment(
        ScenarioConfig(args.seed, args.profile, args.days, args.extension_days)
    )
    if args.dataset_dir:
        from .dataset import export_creation_dataset

        export_creation_dataset(result, args.dataset_dir)
    print(json.dumps(result, default=str, indent=2))
