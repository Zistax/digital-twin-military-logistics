import streamlit as st

import requests

from ml.risk_threshold import RISK_THRESHOLD_DEFAULT, is_high_risk
from config.terminology_loader import load_terminology, translate_term

API_BASE_URL = "http://127.0.0.1:8000"


def main():

    term_map = {}
    try:
        term_map = load_terminology()
    except FileNotFoundError:
        # Terminologia non configurata; useremo i termini canonici
        term_map = {}

    st.set_page_config(
        page_title="Digital Twin Logistico – Rischio Convoglio", page_icon="🚚"
    )

    st.title("Digital Twin Logistico – Rischio Convoglio")
    st.write("""
        Questa UI usa l'API FastAPI locale per calcolare il rischio dei convogli.
        Assicurati di aver avviato il server con:
        `uvicorn src.api.app:app --reload`
        """)

    attack_label = translate_term("attack", term_map)
    breakdown_label = translate_term("breakdown", term_map)

    st.write(f"""
        Il modello stima il rischio per i convogli considerando diversi tipi di eventi
        (es. `{attack_label}`, `{breakdown_label}`, ecc.),
        in base al dataset di addestramento.
        """)

    api_url = st.sidebar.text_input(
        "API base URL",
        value=API_BASE_URL,
        help="Endpoint base dell'API FastAPI (es. http://127.0.0.1:8000)",
    )

    st.sidebar.header("Parametri di scenario")

    total_minutes = st.sidebar.number_input(
        "Durata totale simulazione (minuti)",
        min_value=10,
        max_value=10000,
        value=120,
        step=10,
    )

    timestep_minutes = st.sidebar.number_input(
        "Durata di ogni passo (minuti)",
        min_value=1,
        max_value=1000,
        value=10,
        step=1,
    )

    n_convoys = st.sidebar.number_input(
        "Numero di convogli",
        min_value=1,
        max_value=1000,
        value=5,
        step=1,
    )

    st.sidebar.write("---")
    run_button = st.sidebar.button("Calcola rischio convogli")

    st.write("Parametri correnti:")
    st.write(
        f"- Durata totale: **{total_minutes}** minuti  "
        f"- Timestep: **{timestep_minutes}** minuti  "
        f"- Numero di convogli: **{n_convoys}**"
    )

    if run_button:
        st.write("Calcolo del rischio in corso tramite API...")

        payload = {
            "schema_version": "1.0",
            "total_minutes": int(total_minutes),
            "timestep_minutes": int(timestep_minutes),
            "n_convoys": int(n_convoys),
        }

        try:
            resp = requests.post(f"{api_url}/predict", json=payload, timeout=10)
        except requests.RequestException as exc:
            st.error(f"Errore di comunicazione con l'API: {exc}")
            return

        if resp.status_code != 200:
            st.error(f"L'API ha risposto con status {resp.status_code}: {resp.text}")
            return

        data = resp.json()

        # Estraiamo soglia e risultati
        threshold_used = float(data.get("risk_threshold_used", RISK_THRESHOLD_DEFAULT))
        results = data.get("results", [])

        if not results:
            st.warning("L'API ha restituito una lista vuota di risultati.")
            return

        import pandas as pd

        df_result = pd.DataFrame(results)

        # Se l'API non ha già fornito la colonna is_high_risk, la calcoliamo noi
        if "is_high_risk" not in df_result.columns:
            df_result["is_high_risk"] = df_result["risk_proba"].apply(
                lambda p: is_high_risk(float(p), threshold_used)
            )

        df_result_sorted = df_result.sort_values(
            "risk_proba", ascending=False
        ).reset_index(drop=True)

        st.subheader("Risultati – Probabilità di rischio per convoglio (ordinate)")
        st.write(f"Soglia di rischio usata: **{threshold_used:.2f}**")
        st.dataframe(df_result_sorted)

        st.subheader("Grafico – Probabilità di rischio per convoglio")
        chart_data = df_result_sorted.set_index("convoy_id")["risk_proba"]
        st.bar_chart(chart_data)

        st.subheader("Convogli ad alto rischio")

        high_risk = df_result_sorted[df_result_sorted["is_high_risk"]]

        if high_risk.empty:
            st.info(
                "Nessun convoglio supera la soglia di rischio selezionata "
                f"({threshold_used:.2f})."
            )
        else:
            st.warning(
                "Attenzione: alcuni convogli superano la soglia di rischio "
                f"({threshold_used:.2f}). "
                "Elenco convogli ad alto rischio:"
            )
            st.table(high_risk)


if __name__ == "__main__":
    main()
