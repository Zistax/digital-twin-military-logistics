import streamlit as st

from src.ml.predict import load_risk_model, predict_convoy_risk_proba
from src.ml.risk_threshold import RISK_THRESHOLD_DEFAULT, is_high_risk

def main():
    st.set_page_config(page_title="Digital Twin Logistico – Rischio Convoglio", page_icon="🚚")

    st.title("Digital Twin Logistico – Rischio Convoglio")
    st.write(
        """
        Questa UI ti permette di inserire i parametri di simulazione e calcolare
        le probabilità di rischio per ciascun convoglio usando il modello addestrato.
        """
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
        st.write("Calcolo del rischio in corso...")

        # Carichiamo il modello
        try:
            model = load_risk_model("models/risk_model.pkl")
        except FileNotFoundError as exc:
            st.error(
                f"Impossibile caricare il modello: {exc}. "
                "Assicurati di aver eseguito prima 'python -m src.ml.train_risk_model'."
            )
            return

        # Calcoliamo le probabilità di rischio
        df_result = predict_convoy_risk_proba(
            model,
            total_minutes=int(total_minutes),
            timestep_minutes=int(timestep_minutes),
            n_convoys=int(n_convoys),
        )

        df_result["is_high_risk"] = df_result["risk_proba"].apply(lambda p: is_high_risk(float(p)))
        # Ordiniamo per rischio decrescente
        df_result_sorted = (
            df_result.sort_values("risk_proba", ascending=False)
            .reset_index(drop=True)
        )

        st.subheader("Risultati – Probabilità di rischio per convoglio (ordinate)")
        st.write(f"Soglia di rischio predefinita: **{RISK_THRESHOLD_DEFAULT:.2f}**")
        st.dataframe(df_result_sorted)

        st.subheader("Risultati – Probabilità di rischio per convoglio (ordinate)")
        st.dataframe(df_result_sorted)

        st.subheader("Grafico – Probabilità di rischio per convoglio")

        # Usiamo il convoglio come etichetta sull'asse X
        chart_data = df_result_sorted.set_index("convoy_id")["risk_proba"]

        st.bar_chart(chart_data)

 # Analisi semplice: quali convogli hanno rischio > soglia?
        risk_threshold = 0.5
        high_risk = df_result_sorted[df_result_sorted["risk_proba"] >= risk_threshold]

        st.subheader("Convogli ad alto rischio")

        high_risk = df_result_sorted[df_result_sorted["is_high_risk"]]

        if high_risk.empty:
            st.info(
                f"Nessun convoglio supera la soglia di rischio selezionata ({RISK_THRESHOLD_DEFAULT:.2f})."
            )
        else:
            st.warning(
                f"Attenzione: alcuni convogli superano la soglia di rischio ({RISK_THRESHOLD_DEFAULT:.2f}). "
                "Elenco convogli ad alto rischio:"
            )
            st.table(high_risk)
            
        st.subheader("Risultati – Probabilità di rischio per convoglio")
        st.dataframe(df_result)


if __name__ == "__main__":
    main()