from .config import SimConfig
from .simulator import run_simulation
from src.config.config_loader import load_sim_config


def ask_int(prompt: str, default: int) -> int:
    """Chiede un intero all'utente con un valore di default.

    Se l'utente preme solo Invio oppure inserisce un valore non valido,
    viene restituito il valore di default.
    """
    full_prompt = f"{prompt} [{default}]: "

    user_input = input(full_prompt).strip()
    if user_input == "":
        return default

    try:
        value = int(user_input)
    except ValueError:
        print(f"Valore non valido, uso il default: {default}")
        return default

    if value <= 0:
        print(f"Il valore deve essere > 0. Uso il default: {default}")
        return default

    return value


def main() -> None:
    print(
        "=== Simulatore logistico – Fase 02 (simulatore base, parametri da console) ==="
    )
    print(
        "Premi Invio per accettare i valori di default indicati tra parentesi quadre."
    )
    print()

    sim_conf = load_sim_config()

    default_total_minutes = int(sim_conf.get("total_minutes", 120))
    default_timestep_minutes = int(sim_conf.get("timestep_minutes", 10))
    default_n_convoys = int(sim_conf.get("n_convoys", 5))
    default_depot_capacity = int(sim_conf.get("depot_capacity", 2))

    total_minutes = ask_int("Durata totale simulazione (minuti)", default_total_minutes)
    timestep_minutes = ask_int(
        "Durata di ogni passo (minuti)", default_timestep_minutes
    )
    n_convoys = ask_int("Numero di convogli", default_n_convoys)
    depot_capacity = ask_int("Capacità del deposito", default_depot_capacity)

    # Creiamo una nuova configurazione con i valori scelti
    config = SimConfig(
        simulation_name="console_run",
        total_minutes=total_minutes,
        timestep_minutes=timestep_minutes,
        n_convoys=n_convoys,
        depot_capacity=depot_capacity,
    )

    print()
    print("Eseguo la simulazione con la seguente configurazione:")
    print(f"  Durata totale:     {config.total_minutes} minuti")
    print(f"  Timestep:          {config.timestep_minutes} minuti")
    print(f"  Numero convogli:   {config.n_convoys}")
    print(f"  Capacità deposito: {config.depot_capacity}")
    print()

    events, summary = run_simulation(config, save_to_csv=True)

    print("=== Risultati simulazione ===")
    print(f"Nome simulazione:          {summary['simulation_name']}")
    print(f"Minuto finale simulazione: {summary['final_minute']}")
    print(f"Convogli totali:           {summary['n_convoys']}")
    print(f"Convogli completati:       {summary['n_completed_convoys']}")
    print(f"Convogli non completati:   {summary['n_not_completed_convoys']}")
    print(f"Eventi registrati:         {len(events)}")

    csv_path = summary.get("events_csv_path")
    if csv_path:
        print()
        print(f"Log eventi salvato in: {csv_path}")

    print()
    print(
        (
            "Fase 02: ora puoi lanciare simulazioni cambiando i "
            "parametri direttamente dalla console."
        )
    )


if __name__ == "__main__":
    main()
