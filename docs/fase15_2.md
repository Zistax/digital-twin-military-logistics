# Fase 15 – /optimize & UI scenari (Parte 2, Giorni 4–6, Windows)

> **Obiettivo pratico**  
> Aggiungere una piccola **UI Streamlit dedicata all’ottimizzazione scenari** che:
>
> - interroga l’endpoint `/optimize`,
> - ti permette di scegliere il numero di episodi,
> - mostra i risultati in tabella e, se vuoi, in un grafico semplice,
> - aggiorna il `README.md` e chiude la Fase 15 con un commit.


---

## Struttura Fase 15 – Parte 2

- **Giorno 4** – Nuova app Streamlit `optimize_app.py`
- **Giorno 5** – Test minimo sul motore `evaluate_actions`
- **Giorno 6** – Aggiornare README, prova end‑to‑end e commit Git


---

## Giorno 4 – Nuova app Streamlit `optimize_app.py`

### Obiettivo del giorno
- Creare una UI separata da `dashboard.py` per non complicare troppo il codice,
- usare `requests` per chiamare `POST /optimize`,
- visualizzare i risultati in modo leggibile.


---

### 1. Creare `src\ui\optimize_app.py`

1. In **VS Code**, nella cartella `src\ui`, crea un nuovo file:

   - `optimize_app.py`

2. Inserisci il seguente codice (adattato allo stile che hai già in `dashboard.py`):

```python
from __future__ import annotations

import json
from typing import Any, Dict, List

import requests
import streamlit as st


API_BASE_URL = "http://127.0.0.1:8000"


def call_optimize_api(
    base_url: str,
    n_episodes_per_action: int,
) -> Dict[str, Any]:
    url = base_url.rstrip("/") + "/optimize"
    payload = {
        "schema_version": "1.0",
        "n_episodes_per_action": n_episodes_per_action,
    }

    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    st.set_page_config(page_title="Ottimizzazione scenari convogli", layout="wide")

    st.title("Ottimizzazione scenari / RL scaffolding")

    st.sidebar.header("Configurazione API")
    api_base_url = st.sidebar.text_input("API base URL", API_BASE_URL)

    st.sidebar.header("Parametri ottimizzazione")
    n_episodes = st.sidebar.slider(
        "Episodi per azione",
        min_value=1,
        max_value=10,
        value=2,
        step=1,
    )

    st.markdown(
        """
        Questa pagina esegue l'endpoint **`/optimize`** che confronta le politiche
        logistiche di alto livello definite in `conf/rl/default.yml`.
        """
    )

    if st.button("Esegui ottimizzazione"):
        with st.spinner("Chiamata a /optimize in corso..."):
            try:
                data = call_optimize_api(
                    base_url=api_base_url,
                    n_episodes_per_action=n_episodes,
                )
            except requests.RequestException as exc:  # noqa: PERF203
                st.error(f"Errore nella chiamata all'API /optimize: {exc}")
                return

        st.success("Risultati ricevuti dall'API /optimize.")

        results: List[Dict[str, Any]] = data.get("results", [])
        if not results:
            st.warning("Nessun risultato restituito dall'API.")
            return

        import pandas as pd

        df = pd.DataFrame(results)

        st.subheader("Tabella risultati per azione")
        st.dataframe(df, use_container_width=True)

        # Se le colonne esistono, mostriamo anche un grafico reward vs. convogli non completati
        if "avg_reward" in df.columns and "mean_n_not_completed_convoys" in df.columns:
            st.subheader("Reward vs convogli non completati (piu' in basso a destra = meglio)")

            # Creiamo una semplice scatter plot con Altair (se disponibile) o con il metodo nativo
            try:
                import altair as alt

                chart = (
                    alt.Chart(df)
                    .mark_circle(size=100)
                    .encode(
                        x="mean_n_not_completed_convoys",
                        y="avg_reward",
                        color="action_name",
                        tooltip=list(df.columns),
                    )
                )
                st.altair_chart(chart, use_container_width=True)
            except Exception:
                st.line_chart(
                    df.set_index("mean_n_not_completed_convoys")[["avg_reward"]]
                )

        st.subheader("JSON grezzo (debug)")
        st.code(json.dumps(data, indent=2), language="json")


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\ui\optimize_app.py`
- [ ] La funzione `call_optimize_api` chiama `POST /optimize`
- [ ] La UI mostra una tabella e un grafico di base se ci sono i dati


---

### 2. Prova manuale dell’app `optimize_app.py`

1. Assicurati che l’API FastAPI sia in esecuzione:

```bash
uvicorn src.api.app:app --reload
```

2. Avvia la nuova UI Streamlit:

```bash
streamlit run src/ui/optimize_app.py
```

3. Nel browser:
   - controlla che compaia il titolo,
   - verifica che l’URL API sia `http://127.0.0.1:8000`,
   - scegli `Episodi per azione` (es. 1 o 2),
   - clicca su **“Esegui ottimizzazione”**.

4. Verifica che:
   - compaia la tabella dei risultati,
   - se disponibile, compaia il grafico reward vs convogli non completati,
   - sia visibile anche il JSON grezzo.

**Checklist (fine Giorno 4)**
- [ ] `streamlit run src/ui/optimize_app.py` funziona
- [ ] L’app riesce a chiamare `/optimize` e mostra i risultati


---

## Giorno 5 – Test minimo su `evaluate_actions`

### Obiettivo del giorno
- Aggiungere un test rapido sul motore `evaluate_actions` (già usato da `/optimize`),
- assicurarsi che almeno 1 azione venga valutata.


---

### 1. Creare `tests\test_rl_optimizer.py`

1. In **VS Code**, nella cartella `tests`, crea il file:

   - `test_rl_optimizer.py`

2. Inserisci il seguente contenuto:

```python
from src.rl.optimizer import evaluate_actions


def test_evaluate_actions_basic():
    stats = evaluate_actions(num_episodes_per_action=1)

    # Ci aspettiamo almeno una azione valutata
    assert len(stats) >= 1

    first = stats[0]
    assert hasattr(first, "action_id")
    assert hasattr(first, "avg_reward")
```

3. Salva il file.

**Checklist**
- [ ] Esiste `tests\test_rl_optimizer.py` con un test base su `evaluate_actions`


---

### 2. Eseguire pytest o `run_quality.bat`

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest tests/test_rl_optimizer.py
```

oppure, per tutta la suite:

```bash
pytest
```

o ancora:

```bash
run_quality.bat
```

Assicurati che il nuovo test passi.

**Checklist (fine Giorno 5)**
- [ ] Il test su `evaluate_actions` passa
- [ ] Nessun nuovo errore sui test esistenti


---

## Giorno 6 – README, prova end‑to‑end e commit Git

### Obiettivo del giorno
- Aggiornare il `README.md` con una sezione dedicata alla UI di ottimizzazione,
- fare una prova completa **API + optimize_app**,
- creare un commit Git di fine Fase 15.


---

### 1. Aggiornare README con sezione “UI di ottimizzazione scenari”

Apri `README.md` e aggiungi una sezione simile:

```markdown
## UI di ottimizzazione scenari

Oltre alla dashboard principale, e' disponibile una UI Streamlit dedicata
all'esplorazione delle politiche logistiche di alto livello (scaffolding RL).

- Env di scenario: `src/rl/env.py` (`ConvoyScenarioEnv`)
- Motore di valutazione azioni: `src/rl/optimizer.py`
- Endpoint API: `POST /optimize`
- UI Streamlit: `src/ui/optimize_app.py`

Per eseguire la UI di ottimizzazione:

```bash
streamlit run src/ui/optimize_app.py
```

La UI chiama l'endpoint `/optimize`, che per ciascuna azione definita in
`conf/rl/default.yml` esegue alcune simulazioni e calcola:

- reward medio,
- KPI medi (convogli completati/non completati, tempi medi di completamento),
- risultati visualizzati in tabella e grafici.
```

Adatta il testo se vuoi aggiungere dettagli sui KPI.

Salva il `README.md`.

**Checklist**
- [ ] Il README documenta la UI di ottimizzazione e come lanciarla


---

### 2. Prova end‑to‑end

1. Avvia l’API se non è già in esecuzione:

```bash
uvicorn src.api.app:app --reload
```

2. Avvia la UI di ottimizzazione:

```bash
streamlit run src/ui/optimize_app.py
```

3. Dal browser:
   - scegli 1–2 episodi per azione,
   - esegui l’ottimizzazione,
   - verifica che i risultati siano coerenti (azioni diverse con reward diversi).

4. Se vuoi, incrocia i risultati con la chiamata diretta a `/optimize` da Swagger
   per vedere che i numeri coincidano.

**Checklist**
- [ ] API `/optimize` risponde correttamente
- [ ] `optimize_app.py` mostra risultati consistenti con l’API


---

### 3. Commit Git di fine Fase 15

Nel terminale, dalla root del progetto:

```bash
git status
```

Dovresti vedere, tra gli altri:

- `src/rl/optimizer.py`
- `src/ui/optimize_app.py`
- `tests/test_api_optimize.py`
- `tests/test_rl_optimizer.py`
- `README.md` aggiornato

1. Aggiungi i file:

```bash
git add .
```

2. Crea il commit:

```bash
git commit -m "Fase 15: endpoint /optimize e UI di ottimizzazione scenari"
```

3. Verifica che il working tree sia pulito:

```bash
git status
```

Dovresti vedere: `nothing to commit, working tree clean`.

**Checklist (fine Giorno 6 – fine Fase 15)**
- [ ] Endpoint `/optimize` funzionante e testato
- [ ] UI Streamlit dedicata alla valutazione scenari
- [ ] Test di base sul motore RL (`evaluate_actions`)
- [ ] README aggiornato
- [ ] Commit Git creato per chiudere la Fase 15
