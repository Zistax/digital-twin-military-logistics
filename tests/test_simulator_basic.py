from sim.config import SimConfig
from sim.simulator import run_simulation


def test_run_simulation_basic():
    """Verifica che la simulazione base giri senza errori e produca eventi."""
    config = SimConfig(
        simulation_name="test_run",
        total_minutes=200,
        timestep_minutes=10,
        n_convoys=3,
        depot_capacity=2,
    )

    events, summary = run_simulation(config, save_to_csv=False)

    # Dovrebbe esserci almeno un evento per convoglio (spawn)
    assert len(events) >= config.n_convoys

    # Verifichiamo che il numero di convogli nel summary sia consistente
    assert summary["n_convoys"] == config.n_convoys

    # In questo setup, tutti i convogli dovrebbero completare la missione
    assert summary["n_not_completed_convoys"] == 0
