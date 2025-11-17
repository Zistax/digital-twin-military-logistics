# Fase 10 – API rafforzata (simulate + contract predict) – Parte 2 (Giorni 4–6, Windows)

> **Scopo Parte 2**  
> Collegare davvero i pezzi tra loro:
>
> - far sì che la **UI Streamlit** usi l’endpoint `POST /predict` invece di chiamare direttamente il modello,
> - aggiungere un test base per `/simulate`,
> - aggiornare il `README.md` e chiudere la Fase 10 con un commit Git.

> **Prerequisiti**:
> - Parte 1 (`fase10_1.md`) completata,
> - sai avviare l’API con `uvicorn src.api.app:app --reload`,
> - sai avviare la UI con `streamlit run src/ui/dashboard.py`.


---

## Struttura Fase 10 – Parte 2

- **Giorno 4** – Aggiornare la UI Streamlit per usare l’API `/predict`
- **Giorno 5** – Aggiungere un test semplice per `/simulate` e lanciare `pytest`
- **Giorno 6** – Aggiornare il README e fare il commit Git di fine Fase 10


---

## Giorno 4 – UI Streamlit che chiama l’API `/predict`

### Obiettivo del giorno
- Modificare `src\ui\dashboard.py` in modo che:
  - non carichi più il modello direttamente,
  - chiami invece `POST http://127.0.0.1:8000/predict`,
  - gestisca errori di rete in modo amichevole.


---

### 1. Assicurarsi di avere `requests` installato

Se hai già seguito il passo facoltativo della Parte 1, dovresti averlo.  
Altrimenti:

1. Aggiungi (se non c’è) in `requirements.txt`:

```txt
requests
```

2. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pip install -r requirements.txt
```

**Checklist**
- [ ] `requests` è installato nell’ambiente `.venv`


---

### 2. Aggiornare gli import in `src\ui\dashboard.py`

1. Apri `src\ui\dashboard.py` in VS Code.
2. In cima al file, **rimuovi** (o commenta) gli import diretti del modello:

```python
# from src.ml.predict import load_risk_model, predict_convoy_risk_proba
# from src.ml.risk_threshold import RISK_THRESHOLD_DEFAULT, is_high_risk
```

Li rimetteremo in forma diversa.

3. Aggiungi invece:

```python
import requests
import streamlit as st

from src.ml.risk_threshold import RISK_THRESHOLD_DEFAULT, is_high_risk
```

> Ora la UI userà l’API via HTTP, ma continuerà a conoscere la soglia di rischio di default per la parte di interpretazione.

4. (Opzionale) Definisci una costante per la base URL dell’API, poco sotto gli import:

```python
API_BASE_URL = "http://127.0.0.1:8000"
```

Salva il file.

**Checklist**
- [ ] La UI importa `requests`, `streamlit`, e `RISK_THRESHOLD_DEFAULT`, `is_high_risk`
- [ ] Esiste una costante `API_BASE_URL`


---

### 3. Aggiungere un campo di configurazione API nella UI

All’interno della funzione `main()`, dopo `st.set_page_config(...)`, puoi mostrare/permere di cambiare l’URL base API.

Ad esempio, subito dopo `st.title(...)`, aggiungi:

```python
    st.write(
        """
        Questa UI usa l'API FastAPI locale per calcolare il rischio dei convogli.
        Assicurati di aver avviato il server con:
        `uvicorn src.api.app:app --reload`
        """
    )

    api_url = st.sidebar.text_input(
        "API base URL",
        value=API_BASE_URL,
        help="Endpoint base dell'API FastAPI (es. http://127.0.0.1:8000)",
    )
```

Poi, più sotto, quando userai l’API, farai riferimento a `api_url` invece che a una stringa fissa.

Salva il file.

**Checklist**
- [ ] La sidebar contiene ora un campo “API base URL” con default `API_BASE_URL`


---

### 4. Sostituire la logica di calcolo locale con chiamata HTTP

Nella parte finale di `main()`, dove hai:

```python
    if run_button:
        st.write("Calcolo del rischio in corso...")

        # Carichiamo il modello
        try:
            model = load_risk_model("models/risk_model.pkl")
        except FileNotFoundError as exc:
            st.error(...)
            return

        # Calcoliamo le probabilità di rischio
        df_result = predict_convoy_risk_proba(...)
        ...
```

Sostituisci tutto il blocco `if run_button:` con una versione che usa `requests` verso `/predict`:

```python
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
```

Salva il file.

**Checklist**
- [ ] Il blocco `if run_button:` ora chiama `/predict` via HTTP
- [ ] In caso di errore rete o status code diverso da 200 la UI mostra un messaggio


---

### 5. Riutilizzare il resto della logica (ordinamento, grafico, alto rischio)

Subito dopo `df_result = pd.DataFrame(results)`, puoi riutilizzare (con poche modifiche) la logica che avevi già:

- aggiunta colonna `is_high_risk` (se non è già presente),
- ordinamento per `risk_proba`,
- tabella, grafico, sezione “alto rischio”.

Ad esempio:

```python
        # Se l'API non ha già fornito la colonna is_high_risk, la calcoliamo noi
        if "is_high_risk" not in df_result.columns:
            df_result["is_high_risk"] = df_result["risk_proba"].apply(
                lambda p: is_high_risk(float(p), threshold_used)
            )

        df_result_sorted = (
            df_result.sort_values("risk_proba", ascending=False)
            .reset_index(drop=True)
        )

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
                f"Nessun convoglio supera la soglia di rischio selezionata ({threshold_used:.2f})."
            )
        else:
            st.warning(
                f"Attenzione: alcuni convogli superano la soglia di rischio ({threshold_used:.2f}). "
                "Elenco convogli ad alto rischio:"
            )
            st.table(high_risk)
```

Salva il file.

**Checklist (fine Giorno 4)**
- [ ] La UI non importa più direttamente il modello ML
- [ ] La UI invia una richiesta a `/predict` e visualizza i risultati
- [ ] In caso di problemi con l’API vengono mostrati messaggi chiari


---

## Giorno 5 – Aggiungere un test base per `/simulate`

### Obiettivo del giorno
- Aggiungere un test nel modulo `tests/test_api_basic.py` che verifichi che `/simulate` funzioni con parametri semplici.


---

### 1. Aggiornare `tests\test_api_basic.py`

1. Apri `tests\test_api_basic.py` in VS Code.
2. In fondo al file, aggiungi un nuovo test:

```python
def test_simulate_basic():
    """Verifica che l'endpoint /simulate risponda 200 e contenga i campi principali."""
    payload = {
        "schema_version": "1.0",
        "total_minutes": 60,
        "timestep_minutes": 10,
        "n_convoys": 3,
        "depot_capacity": 2,
        "simulation_name": "test_sim",
    }

    response = client.post("/simulate", json=payload)
    assert response.status_code == 200

    data = response.json()

    # Controlliamo alcuni campi chiave
    assert data["schema_version"] == "1.0"
    assert data["simulation_name"] == "test_sim"
    assert data["total_minutes"] == 60
    assert data["timestep_minutes"] == 10
    assert data["n_convoys"] == 3

    assert "kpi" in data
    kpi = data["kpi"]
    assert "n_convoys" in kpi
    assert "n_completed_convoys" in kpi
    assert "n_not_completed_convoys" in kpi
```

3. Salva il file.

> Il test non controlla il **valore esatto** delle metriche, solo la presenza e coerenza dei campi.  
> Questo lo rende stabile anche se cambierai il simulatore in futuro.


**Checklist**
- [ ] Esiste il test `test_simulate_basic` in `tests\test_api_basic.py`


---

### 2. Eseguire `pytest`

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest
```

Assicurati che:

- passino i test esistenti (sim, ML, API, soglia, ecc.),
- passi anche il nuovo `test_simulate_basic`.

**Checklist (fine Giorno 5)**
- [ ] `pytest` gira senza errori
- [ ] Il nuovo test per `/simulate` è verde


---

## Giorno 6 – Aggiornare README e fare il commit Fase 10

### Obiettivo del giorno
- Documentare nel `README.md` il flusso **API + UI**,
- fare un commit Git che chiuda la Fase 10.


---

### 1. Aggiornare `README.md` con una sezione “Flusso API + UI”

Apri `README.md` nella root del progetto e aggiungi (o aggiorna) una sezione simile:

```markdown
## Flusso API + UI

Il progetto espone un'API FastAPI e una UI Streamlit.

### API FastAPI

- Avvio server (da root progetto, ambiente attivo):

  ```bash
  uvicorn src.api.app:app --reload
  ```

- Endpoint principali:
  - `GET /health` → stato API
  - `POST /predict` / `POST /predict_risk` → rischio convoglio
  - `POST /simulate` → esegue una simulazione e restituisce KPI di base

La documentazione interattiva è disponibile su <http://127.0.0.1:8000/docs>.

### UI Streamlit

- Avvio UI (da root progetto, ambiente attivo):

  ```bash
  streamlit run src/ui/dashboard.py
  ```

- La UI chiama l'endpoint `POST /predict` dell'API, utilizzando come URL base
  il valore configurabile nella sidebar (default `http://127.0.0.1:8000`).

Per usare correttamente la UI è necessario che il server FastAPI sia in esecuzione.
```

Salva il file.

**Checklist**
- [ ] Il README spiega chiaramente come far parlare API e UI


---

### 2. Esecuzione finale dei comandi principali (check veloce)

Fai un giro veloce di comandi (anche solo una volta, non tutti i giorni):

1. Esegui i test:

```bash
pytest
```

2. Avvia l’API in un terminale:

```bash
uvicorn src.api.app:app --reload
```

3. Avvia la UI in un altro terminale:

```bash
streamlit run src/ui/dashboard.py
```

4. Nel browser:
   - Vai su `http://127.0.0.1:8000/docs` e verifica `/predict` e `/simulate`,
   - Vai su `http://localhost:8501` e prova qualche scenario dalla UI
     (assicurandoti che usi l’API corretta).

**Checklist**
- [ ] `pytest` passa
- [ ] API e UI funzionano insieme senza errori evidenti


---

### 3. Commit Git di fine Fase 10

Nel terminale, dalla root del progetto:

```bash
git status
```

Dovresti vedere file nuovi/modificati, fra cui:

- `src/api/app.py`
- `src/ui/dashboard.py`
- `tests/test_api_basic.py`
- `README.md`

1. Aggiungi i file:

```bash
git add .
```

2. Crea il commit:

```bash
git commit -m "Fase 10: API /simulate e integrazione UI con /predict"
```

3. Verifica che il working tree sia pulito:

```bash
git status
```

Dovresti vedere: `nothing to commit, working tree clean`.

**Checklist (fine Giorno 6 – fine Fase 10)**
- [ ] La UI usa l’API `/predict` per il rischio convoglio
- [ ] Esiste l’endpoint `/simulate` con KPI base
- [ ] I test (`pytest`) passano
- [ ] Il README documenta il flusso API + UI
- [ ] È stato creato un commit Git per la Fase 10


---

## Fine Fase 10 – Cosa hai ottenuto

Con la Fase 10 completata hai:

- una **API FastAPI** con endpoint chiari (`/health`, `/predict`, `/simulate`),
- un contratto di richiesta/risposta per il rischio con `schema_version` e soglia esplicita,
- una **UI Streamlit** che non “parla” più direttamente col modello ma con l’API, come farebbe un client reale,
- test di base sia per `/predict` (dalle fasi precedenti) sia per `/simulate`,
- documentazione nel README che descrive il flusso completo.

D’ora in poi puoi:
- migliorare il simulatore e il modello senza toccare la UI,
- aggiungere altri endpoint (es. per analisi di log, scenari salvati, ecc.),
- oppure concentrare le prossime fasi su logging avanzato, DevOps, ottimizzazioni, ecc.
