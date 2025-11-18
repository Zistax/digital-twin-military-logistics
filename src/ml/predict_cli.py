from __future__ import annotations

from .predict import load_risk_model, predict_convoy_risk_proba


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
    print("=== CLI rischio convoglio – Fase 05 ===")
    print("Questo script usa il modello salvato per stimare il rischio dei convogli.")
    print("Premi Invio per usare i valori di default tra parentesi quadre.")
    print()

    # Valori di default semplici (puoi adattarli)
    default_total_minutes = 120
    default_timestep_minutes = 10
    default_n_convoys = 5

    total_minutes = ask_int("Durata totale simulazione (minuti)", default_total_minutes)
    timestep_minutes = ask_int("Durata di ogni passo (minuti)", default_timestep_minutes)
    n_convoys = ask_int("Numero di convogli da valutare", default_n_convoys)

    print()
    print("Carico il modello di rischio da 'models/risk_model.pkl'...")

    try:
        model = load_risk_model("models/risk_model.pkl")
    except FileNotFoundError as exc:
        print(f"ERRORE: {exc}")
        print("Suggerimento: esegui prima 'python -m src.ml.train_risk_model' per creare il modello.")
        return

    print("Calcolo le probabilità di rischio...")
    df_result = predict_convoy_risk_proba(
        model,
        total_minutes=total_minutes,
        timestep_minutes=timestep_minutes,
        n_convoys=n_convoys,
    )

    print()
    print("=== Risultati ===")
    print("Convoglio  Prob_rischio")
    for _, row in df_result.iterrows():
        convoy_id = int(row["convoy_id"])
        prob = float(row["risk_proba"])
        print(f"{convoy_id:8d}  {prob:11.3f}")

    print()
    print("Interpretazione (semplificata):")
    print("- Prob_rischio ~ 0.0  -> convoglio probabilmente 'sicuro' (secondo il modello).")
    print("- Prob_rischio ~ 1.0  -> convoglio probabilmente 'a rischio' di non completare la missione.")
    print()
    print("Nota: in questa versione tutti i convogli hanno le stesse feature,")
    print("quindi spesso avranno la stessa probabilità. In fasi successive aggiungerai feature più ricche.")


if __name__ == "__main__":
    main()