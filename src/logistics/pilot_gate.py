"""Explicit acceptance checks for a small pilot, separate from D03 readiness."""

from math import isfinite


def evaluate_pilot(records, expected_seeds=(0, 1, 2), max_wall_seconds=600):
    expected = {
        (seed, profile)
        for seed in expected_seeds
        for profile in ("regular", "pressure", "perturbed")
    }
    actual = [(r["seed"], r["profile"]) for r in records]
    failures = []
    if set(actual) != expected or len(actual) != len(expected):
        failures.append("missing or duplicated seed/profile run")
    for row in records:
        identity = f"{row['seed']}:{row['profile']}"
        if row.get("valid") is not True:
            failures.append(f"invalid run {identity}")
            continue
        if row.get("unexplained_open_missions") != []:
            failures.append(f"unexplained open missions {identity}")
        if not row.get("trace_rows", 0) or not row.get("trace_sha256"):
            failures.append(f"missing operational trace {identity}")
        seconds = row.get("wall_seconds")
        if (
            type(seconds) not in (int, float)
            or not isfinite(seconds)
            or not 0 < seconds <= max_wall_seconds
        ):
            failures.append(f"runtime outside pilot budget {identity}")
        kpi = row["kpi"]
        if (
            kpi["quota_reached"] + kpi["quota_censored"] + kpi["cancelled"]
            != kpi["missions"]
        ):
            failures.append(f"mission accounting mismatch {identity}")
    valid = [r for r in records if r.get("valid") is True]
    if not any(r["kpi"]["on_time_reached"] > 0 for r in valid) or not any(
        r["kpi"]["known_late"] > 0 for r in valid
    ):
        failures.append("no observed variation in timing outcomes")
    return {
        "pilot_gate_version": 1,
        "expected_seeds": list(expected_seeds),
        "max_wall_seconds_per_run": max_wall_seconds,
        "passed": not failures,
        "failures": failures,
        "scope": (
            "D02 operational pilot; not closure of "
            "F02/F03/D01 or statistical validation"
        ),
        "ready_for_D03": False,
    }
