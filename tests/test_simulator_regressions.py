from src.sim.config import SimConfig
from src.sim.simulator import run_simulation


def test_completion_at_60_and_125_minutes():
    for total in (60, 125, 5):
        events, summary = run_simulation(
            SimConfig(total_minutes=total, timestep_minutes=10, n_convoys=2), False
        )
        assert summary["final_minute"] == total
        assert summary["n_completed_convoys"] == 2
        assert [
            e["minute"] for e in events if e["event_type"] == "convoy_completed"
        ] == [total, total]


def test_csv_outputs_do_not_overwrite_same_second(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = run_simulation(SimConfig(total_minutes=60), True)[1]["events_csv_path"]
    second = run_simulation(SimConfig(total_minutes=60), True)[1]["events_csv_path"]
    assert first != second
    assert (tmp_path / first).exists() and (tmp_path / second).exists()


def test_invalid_legacy_configuration_rejected():
    import pytest

    for field in ("total_minutes", "timestep_minutes", "n_convoys", "depot_capacity"):
        with pytest.raises(ValueError):
            SimConfig(**{field: 0})
