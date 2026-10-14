from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
import time
import weakref

from scripts.produce_d03 import bounded_map, execute_released
from src.logistics.batch import execute_run, make_plan
from src.logistics.bundles import read_verified_bundle
from tests.test_batch import small_run


def test_memory_executor_preserves_every_exported_table_and_releases_result(
    monkeypatch,
):
    class Result(dict):
        pass

    alive = []

    def small_with_reference(config, **kwargs):
        result = Result(small_run(config, **kwargs))
        alive.append(weakref.ref(result))
        return result

    def after_release(path):
        assert alive[-1]() is None
        return read_verified_bundle(path)

    monkeypatch.setattr("src.logistics.batch.run_experiment", small_run)
    monkeypatch.setattr("scripts.produce_d03.run_experiment", small_with_reference)
    monkeypatch.setattr("scripts.produce_d03.read_verified_bundle", after_release)
    plan = make_plan()
    row = plan["runs"][0]
    with TemporaryDirectory() as directory:
        roots = [Path(directory) / name for name in ("baseline", "released")]
        for root in roots:
            for name in ("records", "bundles", "traces"):
                (root / name).mkdir(parents=True)
        before = execute_run((str(roots[0]), row, plan, 1))
        after = execute_released((str(roots[1]), row, plan, 1))
        assert before["valid"] and after["valid"]
        assert before["manifest_sha256"] == after["manifest_sha256"]
        assert before["trace_sha256"] == after["trace_sha256"]
        assert before["kpi"] == after["kpi"]
        assert before["rows"] == after["rows"]


def test_scheduler_caps_simultaneous_pressure_runs_without_dropping_tasks():
    lock = Lock()
    active, peak = 0, 0

    def observed(payload):
        nonlocal active, peak
        heavy = payload[1]["profile"] == "pressure"
        with lock:
            active += heavy
            peak = max(peak, active)
        time.sleep(0.01)
        with lock:
            active -= heavy
        return payload[0]

    payloads = [(i, {"profile": "pressure" if i % 2 else "regular"}) for i in range(20)]
    with ThreadPoolExecutor(max_workers=5) as pool:
        completed = list(bounded_map(pool, observed, payloads, 5, 2))
    assert sorted(completed) == list(range(20))
    assert peak <= 2
