"""Four local operator views of the native /v1 API."""

from uuid import uuid4

import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000"
TABS = (
    "Missioni e previsioni",
    "Depositi e scorte",
    "Flotta e rete",
    "Analisi e qualità modello",
)


def api(method, path, body=None):
    try:
        response = requests.request(
            method,
            st.session_state.get("api_url", API_BASE_URL).rstrip("/") + path,
            json=body,
            timeout=120,
        )
        if not response.ok:
            st.error(f"Richiesta rifiutata ({response.status_code}): {response.text}")
            return None
        return response.json() if response.content else {}
    except requests.RequestException as exc:
        st.error(f"API non disponibile: {exc}")
        return None


def command(route, **fields):
    view = st.session_state["view"]
    result = api(
        "POST",
        f"/v1/sessions/{view['session_id']}/{route}",
        {"command_id": uuid4().hex, "expected_revision": view["revision"], **fields},
    )
    if result is not None:
        st.session_state["view"] = result
        st.rerun()


def main():
    st.set_page_config(
        page_title="Digital Twin Logistico", page_icon="🚚", layout="wide"
    )
    st.title("Digital Twin Logistico")
    st.caption("Demo locale sintetica · tempi in secondi dall'inizio scenario")
    st.sidebar.text_input("API base URL", API_BASE_URL, key="api_url")
    with st.sidebar.form("new-session"):
        seed = st.selectbox("Seed di sviluppo", [0, 1, 2, 3])
        profile = st.selectbox("Profilo", ["regular", "pressure", "perturbed"])
        experimental = st.checkbox("Abilita candidato sperimentale non promosso")
        if st.form_submit_button("Crea sessione"):
            result = api(
                "POST",
                "/v1/sessions",
                {
                    "seed": seed,
                    "profile": profile,
                    "forecast_mode": "experimental" if experimental else "off",
                },
            )
            if result is not None:
                previous = st.session_state.get("view")
                if previous:
                    api("DELETE", f"/v1/sessions/{previous['session_id']}")
                st.session_state["view"] = result
    if "view" not in st.session_state:
        st.info("Avvia l'API locale e crea una sessione dalla barra laterale.")
        return
    view = st.session_state["view"]
    sid = view["session_id"]
    st.sidebar.caption(f"Sessione {sid} · revisione {view['revision']}")
    st.sidebar.metric("Tempo simulato (s)", view["observed_s"])
    if st.sidebar.button("Aggiorna dati"):
        result = api("GET", f"/v1/sessions/{sid}")
        if result is not None:
            st.session_state["view"] = result
            st.rerun()
    if st.sidebar.button("Chiudi sessione"):
        if api("DELETE", f"/v1/sessions/{sid}") is not None:
            del st.session_state["view"]
            st.rerun()
    editable = view["valid"] and view["observed_s"] < view["horizon_s"]
    if st.sidebar.button("Avanza di un'ora", disabled=not editable):
        command("advance", target_s=min(view["observed_s"] + 3600, view["horizon_s"]))
    st.warning(view["forecast_label"])
    if not view["valid"]:
        st.error("Simulazione invalidata: crea una nuova sessione.")
    tabs = st.tabs(TABS)
    with tabs[0]:
        st.caption(
            f"Fatti osservati fino a t={view['facts_cutoff_s']} s. "
            "Ogni stima ha il proprio timestamp."
        )
        catalog = api("GET", "/v1/catalog")
        if catalog:
            with st.expander("Nuova missione manuale"):
                with st.form("mission"):
                    origin = st.selectbox("Origine", catalog["depots"])
                    destination = st.selectbox(
                        "Destinazione", catalog["depots"], index=2
                    )
                    item = st.selectbox(
                        "Articolo", [i["item_id"] for i in catalog["items"]]
                    )
                    quantity = st.number_input(
                        "Quantità richiesta", min_value=1, max_value=1000, value=10
                    )
                    deadline = st.number_input(
                        "Scadenza assoluta (s)",
                        min_value=view["observed_s"] + 1,
                        max_value=259200,
                        value=view["observed_s"] + 86400,
                    )
                    urgent = st.checkbox("Urgente")
                    st.caption(
                        "La quota minima usa la soglia di catalogo. "
                        "L’API segnala i campi non validi."
                    )
                    if st.form_submit_button(
                        "Registra missione", disabled=not editable
                    ):
                        command(
                            "missions",
                            origin_id=origin,
                            destination_id=destination,
                            quantities={item: int(quantity)},
                            deadline_s=int(deadline),
                            urgent=urgent,
                        )
        for mission in view["missions"]:
            with st.expander(
                f"{mission['mission_id']} · {mission['phase']} · "
                f"scadenza {mission['deadline_s']} s"
            ):
                st.write(f"{mission['origin_id']} → {mission['destination_id']}")
                st.write(mission["explanation"])
                if mission["waiting_reason"]:
                    st.caption("Attesa: " + mission["waiting_reason"])
                st.dataframe(mission["lines"], hide_index=True)
                st.write("Esito osservato (null = ancora sconosciuto)")
                st.json(mission["outcome"])
                st.write("Ultima previsione e motivi di astensione")
                st.json(mission["prediction"])
                st.write("Storico e stima iniziale di pianificazione")
                st.json(mission["prediction_history"])
                st.json(mission["creation_estimate"])
                reason = st.text_input(
                    "Motivo annullamento", key="reason-" + mission["mission_id"]
                )
                if st.button(
                    "Annulla missione",
                    key="cancel-" + mission["mission_id"],
                    disabled=not view["valid"],
                ):
                    command(
                        "cancellations", mission_id=mission["mission_id"], reason=reason
                    )
        st.subheader("Richieste di approvazione")
        for rid, request in view["approvals"]["requests"].items():
            st.write(rid, request)
            if request["status"] in ("pending", "deferred", "rejected"):
                decision = st.selectbox(
                    "Decisione", ["approve", "defer", "reject"], key="decision-" + rid
                )
                if st.button(
                    "Invia decisione", key="send-" + rid, disabled=not view["valid"]
                ):
                    command("decisions", request_id=rid, decision=decision)
    with tabs[1]:
        for depot in view["depots"]:
            with st.expander(depot["depot_id"], expanded=True):
                st.write(
                    f"Banchine: {depot['berths_used']}/{depot['berths']} · "
                    f"coda: {depot['queue_size']}"
                )
                st.dataframe(
                    [
                        {
                            "item_id": i,
                            "stock": depot["stock"].get(i, 0),
                            "available": q,
                            "reserved": depot["reserved"][i],
                            "quarantine": depot["quarantine"].get(i, 0),
                        }
                        for i, q in depot["available"].items()
                    ],
                    hide_index=True,
                )
                st.json(
                    {
                        k: depot[k]
                        for k in (
                            "capacity_m3",
                            "occupied_m3",
                            "opening_now",
                            "local_backlog",
                            "incoming",
                        )
                    }
                )
    with tabs[2]:
        st.caption(
            "Posizione nodale o tratta osservata. "
            "Nessuna coordinata GPS simulata presentata come misura."
        )
        st.dataframe(
            [
                {
                    k: v[k]
                    for k in (
                        "vehicle_id",
                        "position_node",
                        "broken",
                        "cold",
                        "max_kg",
                        "max_m3",
                    )
                }
                for v in view["fleet"]
            ],
            hide_index=True,
        )
        for vehicle in view["fleet"]:
            with st.expander(vehicle["vehicle_id"] + " · percorso e carichi"):
                st.json(vehicle)
        with st.expander("Rete, traffico e meteo osservati"):
            st.json(view["network"])
    with tabs[3]:
        for limitation in view["limitations"]:
            st.write("• " + limitation)
        st.subheader("KPI e tempi osservati della sessione")
        st.json(view["analysis"])
        st.caption(
            "Puntualità tra quote raggiunte; "
            "aperte e annullate hanno conteggi separati."
        )
        quality = api("GET", "/v1/model-quality")
        if quality:
            st.subheader("Valutazione indipendente M03 · dati sintetici storici")
            st.write("Modello attivo:", quality["active"])
            st.dataframe(
                [
                    {
                        "canale": c,
                        **{
                            k: m.get(k)
                            for k in (
                                "brier",
                                "baseline_brier",
                                "ece",
                                "mae_minutes",
                                "baseline_mae_minutes",
                                "coverage",
                                "width_minutes",
                            )
                        },
                    }
                    for c, m in quality["evaluation"]["channels_with_policy"].items()
                ],
                hide_index=True,
            )
            st.caption(
                "Durate e ampiezze in minuti. "
                "Intervalli larghi non implicano promozione."
            )
            with st.expander("Calibrazione, segmenti, gate e rapporto completo"):
                st.json(quality)


if __name__ == "__main__":
    main()
