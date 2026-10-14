import pandas as pd

from src.sim.metrics import compute_basic_kpis


def test_compute_basic_kpis_all_completed():
    """Tutti i convogli completano la missione."""
    data = [
        {"event_type": "convoy_spawned", "convoy_id": 1, "minute": 0},
        {"event_type": "convoy_spawned", "convoy_id": 2, "minute": 0},
        {"event_type": "convoy_completed", "convoy_id": 1, "minute": 30},
        {"event_type": "convoy_completed", "convoy_id": 2, "minute": 40},
    ]
    df = pd.DataFrame(data)

    kpis = compute_basic_kpis(df)

    assert kpis["n_convoys"] == 2
    assert kpis["n_completed_convoys"] == 2
    assert kpis["n_not_completed_convoys"] == 0
    assert kpis["min_completion_minute"] == 30.0
    assert kpis["max_completion_minute"] == 40.0


def test_compute_basic_kpis_some_not_completed():
    """Alcuni convogli non completano la missione."""
    data = [
        {"event_type": "convoy_spawned", "convoy_id": 1, "minute": 0},
        {"event_type": "convoy_spawned", "convoy_id": 2, "minute": 0},
        {"event_type": "convoy_completed", "convoy_id": 1, "minute": 30},
        # Il convoglio 2 non ha eventi di completamento
    ]
    df = pd.DataFrame(data)

    kpis = compute_basic_kpis(df)

    assert kpis["n_convoys"] == 2
    assert kpis["n_completed_convoys"] == 1
    assert kpis["n_not_completed_convoys"] == 1
    assert kpis["min_completion_minute"] == 30.0
    assert kpis["max_completion_minute"] == 30.0


def test_compute_basic_kpis_no_completed():
    """Nessun convoglio completa la missione."""
    data = [
        {"event_type": "convoy_spawned", "convoy_id": 1, "minute": 0},
        {"event_type": "convoy_spawned", "convoy_id": 2, "minute": 0},
    ]
    df = pd.DataFrame(data)

    kpis = compute_basic_kpis(df)

    assert kpis["n_convoys"] == 2
    assert kpis["n_completed_convoys"] == 0
    assert kpis["n_not_completed_convoys"] == 2
    assert kpis["avg_completion_minute"] is None
    assert kpis["min_completion_minute"] is None
    assert kpis["max_completion_minute"] is None
