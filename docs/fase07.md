# Fase 07 – UI Web semplice per il rischio convoglio (Streamlit, Windows, Giorni 1–4)

> **Scopo Fase 07**  
> Creare una **piccola interfaccia web** (locale) che ti permetta di:
>
> - inserire parametri di scenario (durata, timestep, numero convogli),
> - usare il **modello di rischio** già addestrato,
> - vedere in una tabella e in un grafico le **probabilità di rischio** dei convogli,
> - farlo in modo semplice, cliccando pulsanti, senza ricordarti i comandi da terminale.
>
> Useremo **Streamlit**, che è pensato proprio per creare UI semplici in Python.

> **Prerequisiti** (da fasi precedenti):
> - `python -m src.ml.train_risk_model` funziona e crea `models\risk_model.pkl`
> - `python -m src.ml.predict_cli` funziona
> - `pytest` gira senza errori
> - il progetto ha già la struttura `src\ui\` creata in Fase 02 (con `__init__.py`).

---

## Struttura Fase 07

- **Giorno 1** – Installare Streamlit e creare lo scheletro della UI
- **Giorno 2** – Collegare la UI al modello di rischio e mostrare la tabella
- **Giorno 3** – Aggiungere grafico bar-chart delle probabilità e qualche miglioramento
- **Giorno 4** – Test manuali, aggiornare README e fare il commit Git di fine Fase 07

---

## Giorno 1 – Installare Streamlit e creare lo scheletro UI

### Obiettivo del giorno
- Aggiungere **Streamlit** alle dipendenze del progetto,
- creare il file `src\ui\dashboard.py`,
- verificare che la UI si apra (anche se ancora vuota).

---

### 1. Aggiungere Streamlit a `requirements.txt`

1. Apri `requirements.txt` nella root del progetto (in VS Code).
2. Aggiungi una riga (se non esiste ancora):

```txt
streamlit
```

3. Salva il file.

**Checklist**
- [x] `requirements.txt` contiene anche la voce `streamlit`

---

### 2. Installare Streamlit nell'ambiente `.venv`

1. Apri **PowerShell** o **cmd**.
2. Vai nella cartella del progetto (sostituisci `TUO_UTENTE`):

```bash
cd C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico
```

3. Attiva l'ambiente virtuale `.venv`:

- PowerShell:
  ```bash
  .venv\Scripts\Activate.ps1
  ```
- cmd:
  ```bat
  .venv\Scripts\activate.bat
  ```

4. Installa/aggiorna i pacchetti:

```bash
pip install -r requirements.txt
```

Attendi la fine dell'installazione (potrebbe richiedere un po', la prima volta).

**Checklist**
- [x] Ambiente `.venv` attivo
- [x] `pip install -r requirements.txt` eseguito senza errori critici

---

### 3. Creare `src\ui\dashboard.py` (scheletro UI)

1. Apri **VS Code**.
2. Nella barra laterale, espandi `src` → `ui`.
3. Crea un nuovo file chiamato `dashboard.py`.
4. Inserisci il seguente contenuto **minimo**:

```python
import streamlit as st


def main():
    st.set_page_config(page_title="Digital Twin Logistico – Rischio Convoglio", page_icon="🚚")

    st.title("Digital Twin Logistico – Rischio Convoglio")
    st.write(
        """
        Questa è una prima versione della UI web per esplorare le probabilità di rischio dei convogli.
        Nelle prossime giornate collegherai questa pagina al modello di rischio che hai addestrato.
        """
    )


if __name__ == "__main__":
    main()
```

5. Salva il file (`Ctrl + S`).

**Checklist**
- [x] Esiste `src\ui\dashboard.py`
- [x] Il file contiene una funzione `main()` con `st.title(...)` e una descrizione

---

### 4. Avviare la UI Streamlit

1. Nel terminale (con `.venv` attivo), assicurati di essere nella cartella del progetto:

```bash
cd C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico
```

2. Avvia Streamlit puntando al file `src\ui\dashboard.py`:

```bash
streamlit run src/ui/dashboard.py
```

3. Dopo qualche secondo, dovresti vedere nel terminale un messaggio tipo:

```text
  Local URL: http://localhost:8501
```

4. Apri il browser e visita:

```text
http://localhost:8501
```

Dovresti vedere il titolo e la descrizione della UI.

> **Nota**: lascia il terminale con Streamlit aperto finché vuoi che l'app rimanga attiva.
> Per fermarla, premi `Ctrl + C` nel terminale.

**Checklist (fine Giorno 1)**
- [x] `streamlit run src/ui/dashboard.py` parte senza errori
- [x] Vedo la pagina con titolo e testo introduttivo su `http://localhost:8501`

---

## Giorno 2 – Collegare la UI al modello di rischio e mostrare la tabella

### Obiettivo del giorno
- Aggiungere controlli nella UI (slider / number input) per scegliere:
  - `total_minutes`
  - `timestep_minutes`
  - `n_convoys`
- Caricare il modello di rischio con `load_risk_model`
- Calcolare le probabilità con `predict_convoy_risk_proba`
- Mostrare una tabella con i risultati

---

### 1. Importare le funzioni di prediction nel dashboard

Apri `src\ui\dashboard.py` e aggiungi (sopra o sotto `import streamlit as st`) questo import:

```python
from src.ml.predict import load_risk_model, predict_convoy_risk_proba
```

Il blocco iniziale del file diventerà simile a:

```python
import streamlit as st

from src.ml.predict import load_risk_model, predict_convoy_risk_proba
```

**Checklist**
- [x] `dashboard.py` importa `load_risk_model` e `predict_convoy_risk_proba`

---

### 2. Aggiungere controlli UI per i parametri di scenario

Sostituisci la funzione `main()` con questa versione (puoi copiare e incollare sostituendo tutto il corpo della funzione):

```python
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
        f"- Durata totale: **{total_minutes}** minuti  
"
        f"- Timestep: **{timestep_minutes}** minuti  
"
        f"- Numero di convogli: **{n_convoys}**"
    )

    if run_button:
        st.write("Calcolo del rischio in corso...")
```

Salva il file.

**Checklist**
- [x] La sidebar contiene 3 campi numerici per i parametri
- [x] È presente il pulsante `Calcola rischio convogli`
- [x] Viene mostrato un riepilogo dei parametri nel corpo della pagina

---

### 3. Collegare il pulsante al modello e mostrare la tabella

Ora aggiungiamo la logica che verrà eseguita quando l’utente clicca il pulsante.

Sotto la riga `if run_button:` aggiungi questo blocco:

```python
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

        st.subheader("Risultati – Probabilità di rischio per convoglio")
        st.dataframe(df_result)
```

Assicurati che il codice sia correttamente indentato (tutto dentro il blocco `if run_button:`).  
Salva il file.

---

### 4. Provare la UI con il modello reale

1. Assicurati che esista il modello addestrato:
   - se non sei sicuro, nel terminale (con `.venv` attivo) esegui:

   ```bash
   python -m src.ml.train_risk_model
   ```

2. Nel terminale, avvia (o riavvia) Streamlit:

```bash
streamlit run src/ui/dashboard.py
```

3. Nel browser (`http://localhost:8501`):

   - modifica i parametri nella sidebar,
   - clicca su **Calcola rischio convogli**,
   - dovresti vedere una tabella con `convoy_id` e `risk_proba`.

**Checklist (fine Giorno 2)**
- [x] La UI mostra una sidebar con i parametri e un pulsante
- [x] Cliccando sul pulsante viene caricato il modello senza errori
- [x] Vedo una tabella con le probabilità di rischio per ogni convoglio

---

## Giorno 3 – Grafico delle probabilità e piccoli miglioramenti

### Obiettivo del giorno
- Aggiungere un **grafico a barre** per visualizzare le probabilità di rischio,
- ordinare la tabella per rischio decrescente,
- evidenziare (a livello testuale) convogli con rischio alto.

---

### 1. Ordinare la tabella per `risk_proba`

In `dashboard.py`, dentro il blocco `if run_button:` **dopo** la riga:

```python
df_result = predict_convoy_risk_proba(...)
```

sostituisci la parte di visualizzazione con questa versione:

```python
        # Ordiniamo per rischio decrescente
        df_result_sorted = df_result.sort_values("risk_proba", ascending=False).reset_index(drop=True)

        st.subheader("Risultati – Probabilità di rischio per convoglio (ordinate)")
        st.dataframe(df_result_sorted)
```

Ricontrolla che la variabile usata più avanti (per il grafico) sia `df_result_sorted`.  
Salva il file.

**Checklist**
- [x] La tabella ora è ordinata per `risk_proba` decrescente

---

### 2. Aggiungere un grafico a barre con Streamlit

Sempre dentro il blocco `if run_button:`, **subito dopo** la `st.dataframe(df_result_sorted)`, aggiungi:

```python
        st.subheader("Grafico – Probabilità di rischio per convoglio")

        # Usiamo il convoglio come etichetta sull'asse X
        chart_data = df_result_sorted.set_index("convoy_id")["risk_proba"]

        st.bar_chart(chart_data)
```

Questo crea un semplice bar-chart usando le funzionalità integrate di Streamlit.

**Checklist**
- [x] Dopo la tabella, vedo un grafico a barre con un valore per ogni convoglio

---

### 3. Evidenziare convogli ad alto rischio a livello testuale

Infine, aggiungi una sezione testuale che segnali quali convogli hanno rischio sopra una certa soglia (es. 0.5).

Sotto il `st.bar_chart(chart_data)` aggiungi:

```python
        # Analisi semplice: quali convogli hanno rischio > soglia?
        risk_threshold = 0.5
        high_risk = df_result_sorted[df_result_sorted["risk_proba"] >= risk_threshold]

        st.subheader("Convogli ad alto rischio (soglia >= 0.5)")

        if high_risk.empty:
            st.info("Nessun convoglio supera la soglia di rischio selezionata (0.5).")
        else:
            st.warning(
                "Attenzione: alcuni convogli superano la soglia di rischio (0.5). "
                "Elenco convogli ad alto rischio:"
            )
            st.table(high_risk)
```

Salva il file.

---

### 4. Provare i miglioramenti nella UI

1. Nel terminale, assicurati che Streamlit sia in esecuzione (`streamlit run ...`), oppure riavvialo.
2. Nel browser (`http://localhost:8501`):
   - Cambia i parametri nella sidebar,
   - Clicca su **Calcola rischio convogli**,
   - Controlla:
     - tabella ordinata per `risk_proba`,
     - grafico a barre,
     - sezione convogli ad alto rischio.

> Se vedi sempre le stesse probabilità per tutti i convogli, è normale: nella versione attuale del modello tutti i convogli condividono le stesse feature. Il valore assoluto della probabilità può comunque cambiare variando i parametri di scenario.

**Checklist (fine Giorno 3)**
- [x] La UI mostra tabella ordinata per rischio
- [x] Vedo un grafico a barre delle probabilità di rischio
- [x] Posso vedere (se presenti) i convogli con rischio >= 0.5 in una tabella dedicata

---

## Giorno 4 – Test manuali, README e commit Fase 07

### Obiettivo del giorno
- Testare manualmente la UI con alcuni scenari,
- Aggiornare il `README.md` con le istruzioni per avviare la UI,
- Fare un **commit Git** che chiuda la Fase 07.

---

### 1. Testare alcuni scenari “tipo” nella UI

Con `streamlit run src/ui/dashboard.py` attivo, prova:

1. **Scenario 1 – Normale**
   - `total_minutes = 120`
   - `timestep_minutes = 10`
   - `n_convoys = 5`

2. **Scenario 2 – Durata breve**
   - `total_minutes = 30`
   - `timestep_minutes = 10`
   - `n_convoys = 5`

3. **Scenario 3 – Più convogli**
   - `total_minutes = 120`
   - `timestep_minutes = 10`
   - `n_convoys = 20`

Per ogni scenario, osserva:
- come cambia (se cambia) la distribuzione delle probabilità,
- se la sezione “convogli ad alto rischio” si popola o rimane vuota.

**Checklist**
- [x] Ho provato almeno 2–3 scenari diversi nella UI senza errori
- [x] Ho capito come interpretare tabella e grafico (anche se il modello è ancora semplice)

---

### 2. Aggiornare `README.md` con una sezione UI

Apri `README.md` nella root del progetto e aggiungi una sezione simile a questa:

```markdown
## UI Web (Streamlit) – Rischio Convoglio

Per avviare una semplice interfaccia web che permette di inserire i parametri di scenario
e vedere la probabilità di rischio per ciascun convoglio:

1. Attiva l'ambiente virtuale:

   ```bash
   .venv\Scripts\activate.bat
   ```

   (oppure, in PowerShell: `.venv\Scripts\Activate.ps1`)

2. Avvia Streamlit dalla root del progetto:

   ```bash
   streamlit run src/ui/dashboard.py
   ```

3. Apri il browser all'indirizzo: <http://localhost:8501>

La pagina permette di:

- impostare `total_minutes`, `timestep_minutes`, `n_convoys`,
- calcolare le probabilità di rischio usando il modello `models/risk_model.pkl`,
- vedere una tabella ordinata per rischio e un grafico a barre,
- evidenziare i convogli con rischio maggiore di una soglia (es. 0.5).
```

Salva il `README.md`.

**Checklist**
- [x] `README.md` contiene una sezione che spiega come avviare la UI Streamlit

---

### 3. Commit Git di fine Fase 07

1. Nel terminale (non serve ambiente attivo per Git, ma non dà fastidio), dalla cartella del progetto:

```bash
git status
```

2. Dovresti vedere file nuovi/modificati, fra cui:
   - `src/ui/dashboard.py`
   - `requirements.txt` (per `streamlit`)
   - `README.md`

3. Aggiungi i file:

```bash
git add .
```

4. Crea un commit con un messaggio chiaro, ad esempio:

```bash
git commit -m "Fase 07: UI web Streamlit per il rischio convoglio"
```

5. Verifica che il working tree sia pulito:

```bash
git status
```

Dovresti vedere: `nothing to commit, working tree clean`.

**Checklist (fine Giorno 4 – fine Fase 07)**

- [ ] Posso avviare la UI con `streamlit run src/ui/dashboard.py`
- [ ] La UI mostra parametri, tabella, grafico, convogli ad alto rischio
- [ ] Il `README.md` è aggiornato con le istruzioni per la UI
- [ ] Ho creato il commit Git “Fase 07: UI web Streamlit per il rischio convoglio”

---

## Fine Fase 07 – Cosa hai ottenuto

Al termine di questa fase hai:

- un **modello di rischio** addestrato,
- una **CLI** da terminale per stimare il rischio (`python -m src.ml.predict_cli`),
- una **API REST** per usi più avanzati (`uvicorn src.api.app:app --reload`),
- una **UI web semplice** (Streamlit) che ti permette di:
  - impostare parametri di scenario,
  - vedere immediatamente le probabilità di rischio,
  - guardare la distribuzione dei rischi in forma di tabella + grafico.

Nelle fasi successive potrai:
- migliorare il simulatore e il dataset per rendere il modello più informativo,
- aggiungere altre pagine alla UI (es. per visualizzare i log, i KPI, i risultati delle simulazioni),
- eventualmente integrare meglio Streamlit e API (o costruire una UI custom su FastAPI).
