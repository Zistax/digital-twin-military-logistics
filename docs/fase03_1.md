# Fase 03 – Analisi log e KPI base (Windows) – Parte 1 (Giorni 1–4)

> **Scopo Fase 03**  
> Imparare a leggere i file CSV generati dal simulatore, analizzarli con Jupyter Notebook e calcolare **prime metriche (KPI)** e **grafici semplici**.

In **Parte 1** (questo file) farai:

- Giorno 1 – Avviare Jupyter Notebook su Windows
- Giorno 2 – Caricare il CSV degli eventi in un notebook
- Giorno 3 – Calcolare KPI di base nel notebook
- Giorno 4 – Creare grafici semplici (istogramma + curva cumulativa)

> Assicurati di aver completato la **Fase 02**: il comando `python -m src.sim.main_sim` deve funzionare e creare un CSV in `data\raw`.

---

## Giorno 1 – Avviare Jupyter Notebook su Windows

### Obiettivo del giorno
- Verificare che Jupyter sia installato e funzionante
- Creare un primo notebook dentro `notebooks`

---

### 1. Attivare l’ambiente virtuale e andare nella cartella del progetto

1. Apri **PowerShell** o **cmd**.
2. Esegui (sostituisci `TUO_UTENTE` col tuo utente):

```bash
cd C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico
```

3. Attiva l’ambiente `.venv`:

- PowerShell:
  ```bash
  .venv\Scripts\Activate.ps1
  ```
- cmd:
  ```bat
  .venv\Scripts\activate.bat
  ```

**Checklist**
- [ ] Sono nella cartella `digital-twin-logistico`
- [ ] Vedo `(.venv)` davanti al prompt

---

### 2. Verificare che Jupyter sia disponibile

Nel terminale (con `.venv` attivo):

```bash
jupyter --version
```

Se vedi una versione (es. `jupyter core : 5.x.x`), è ok.

Se non funziona:
- controlla che nel file `requirements.txt` ci sia `jupyter`
- esegui di nuovo:

```bash
pip install -r requirements.txt
```

**Checklist**
- [ ] `jupyter --version` mostra una versione
- [ ] Nessun errore grave nell’installazione

---

### 3. Avviare Jupyter Notebook

Sempre nella cartella del progetto, con `.venv` attivo:

```bash
jupyter notebook
```

- Si aprirà il browser (di solito `http://localhost:8888`).
- Vedrai un elenco di cartelle e file del progetto.

Se non si apre il browser, copia l’URL mostrato nel terminale e incollalo nel browser.

**Checklist**
- [ ] Jupyter si avvia e vedo l’interfaccia nel browser

---

### 4. Creare un notebook per l’analisi eventi

Nell’interfaccia di Jupyter nel browser:

1. Entra nella cartella `notebooks`.
2. In alto a destra, clicca su **New** → **Python 3 (ipykernel)** (o nome simile).
3. Rinominare il notebook:
   - Clicca sul titolo in alto (es. `Untitled`)
   - Cambialo in: `analisi_eventi_base.ipynb`

Nel primo “cella” del notebook, scrivi:

```python
import sys
print(sys.version)
```

Esegui la cella (Shift+Invio). Dovresti vedere la versione di Python.

**Checklist (fine Giorno 1)**
- [ ] Jupyter si avvia dal progetto
- [ ] Ho creato il notebook `analisi_eventi_base.ipynb` dentro `notebooks`
- [ ] Ho eseguito una cella che stampa la versione di Python

---

## Giorno 2 – Caricare il CSV degli eventi in un notebook

### Obiettivo del giorno
- Generare (o ri-generare) un CSV di eventi con il simulatore
- Caricare il CSV in un DataFrame pandas nel notebook

---

### 1. Generare un CSV aggiornato con il simulatore

1. Nel terminale (con `.venv` attivo), se Jupyter è ancora aperto lascialo pure aperto.
2. Esegui il simulatore:

```bash
python -m src.sim.main_sim
```

3. Inserisci alcuni valori (oppure premi Invio per i default).  
4. Alla fine, dovresti vedere una riga tipo:

```text
Log eventi salvato in: data\raw\sim_events_2025XXXX_XXXXXX.csv
```

> **Segna il percorso esatto del file**, ad esempio:  
> `data\raw\sim_events_20250101_153000.csv`

**Checklist**
- [ ] Ho eseguito `python -m src.sim.main_sim`
- [ ] Ho preso nota del percorso del CSV generato

---

### 2. Caricare il CSV nel notebook con pandas

Torna nel browser, sul notebook `analisi_eventi_base.ipynb`.

1. Nella **prima cella utile** (sotto quella della versione Python), scrivi:

```python
import pandas as pd
```

Esegui la cella (Shift+Invio).

2. Nella cella successiva, definisci il percorso del file CSV.  
   Sostituisci `NOME_FILE.csv` col nome reale:

```python
csv_path = "../data/raw/sim_events_20250101_153000.csv"  # <-- modifica qui
```

> Suggerimento: in Jupyter si usa `../` per salire dalla cartella `notebooks` alla cartella principale del progetto.

3. Nella cella successiva, carica il CSV:

```python
df = pd.read_csv(csv_path)
df.head()
```

4. Esegui la cella.  
   Dovresti vedere le prime 5 righe del DataFrame con colonne tipo:
   - `event_type`
   - `convoy_id`
   - `minute`
   - `step_index`
   - `progress`

**Checklist**
- [ ] Ho importato `pandas` nel notebook
- [ ] Ho definito `csv_path` con il percorso giusto (attenzione a `../`)
- [ ] `df = pd.read_csv(csv_path)` funziona
- [ ] `df.head()` mostra le prime righe senza errori

---

### 3. Controlli base sul DataFrame

Aggiungi alcune celle col codice seguente e esegui una per volta:

```python
# Numero di righe
len(df)
```

```python
# Nomi delle colonne
df.columns.tolist()
```

```python
# Tipi di dati delle colonne
df.dtypes
```

```python
# Valori distinti del tipo di evento
df["event_type"].value_counts()
```

**Checklist (fine Giorno 2)**
- [ ] Posso vedere il numero di righe del DataFrame
- [ ] Vedo la lista delle colonne
- [ ] Vedo i tipi di dati (`dtypes`)
- [ ] Vedo la distribuzione degli `event_type`

---

## Giorno 3 – Calcolare KPI di base nel notebook

### Obiettivo del giorno
Calcolare alcune metriche (KPI) importanti a partire dal DataFrame:
- numero di convogli,
- numero di convogli completati,
- numero di convogli non completati,
- tempo di completamento per convoglio (minimo, massimo, media).

---

### 1. Numero di convogli e completamenti

Aggiungi ed esegui queste celle nel notebook (sotto le precedenti):

```python
# Numero totale di convogli (id distinti)
n_convoys = df["convoy_id"].nunique()
n_convoys
```

```python
# Eventi di completamento
df_completed = df[df["event_type"] == "convoy_completed"]

n_completed_events = len(df_completed)
n_completed_events
```

```python
# Convogli completati (id distinti nei completamenti)
n_completed_convoys = df_completed["convoy_id"].nunique()
n_completed_convoys
```

```python
# Convogli non completati
n_not_completed_convoys = n_convoys - n_completed_convoys
n_not_completed_convoys
```

**Checklist**
- [ ] Ho calcolato `n_convoys`
- [ ] Ho creato `df_completed`
- [ ] Ho calcolato `n_completed_convoys`
- [ ] Ho calcolato `n_not_completed_convoys`

---

### 2. Tempo di completamento per convoglio

Dall’evento `convoy_completed` possiamo estrarre il minuto di completamento.

Aggiungi ed esegui:

```python
# Minuto di completamento per ogni convoglio (se c'è un evento di completamento)
completion_minutes_by_convoy = (
    df_completed
    .groupby("convoy_id")["minute"]
    .min()
)

completion_minutes_by_convoy
```

Per calcolare statistiche di base:

```python
avg_completion_minute = completion_minutes_by_convoy.mean()
max_completion_minute = completion_minutes_by_convoy.max()
min_completion_minute = completion_minutes_by_convoy.min()

avg_completion_minute, min_completion_minute, max_completion_minute
```

**Checklist**
- [ ] Ho creato `completion_minutes_by_convoy`
- [ ] Ho calcolato media, minimo e massimo del minuto di completamento

---

### 3. Riassunto in un dizionario KPI

Per preparare il lavoro della Parte 2 (dove creerai un modulo Python), puoi già creare un piccolo riassunto sotto forma di dizionario nel notebook:

```python
kpis = {
    "n_convoys": int(n_convoys),
    "n_completed_convoys": int(n_completed_convoys),
    "n_not_completed_convoys": int(n_not_completed_convoys),
    "avg_completion_minute": float(avg_completion_minute) if n_completed_convoys > 0 else None,
    "min_completion_minute": float(min_completion_minute) if n_completed_convoys > 0 else None,
    "max_completion_minute": float(max_completion_minute) if n_completed_convoys > 0 else None,
}

kpis
```

**Checklist (fine Giorno 3)**
- [ ] Ho un dizionario `kpis` con i principali indicatori
- [ ] I valori hanno senso (es. numero convogli in linea con la configurazione usata)

---

## Giorno 4 – Grafici semplici (istogramma + curva cumulativa)

### Obiettivo del giorno
Usare **matplotlib** nel notebook per:
- creare un istogramma dei tempi di completamento,
- creare una curva cumulativa dei convogli completati nel tempo.

---

### 1. Importare matplotlib e attivare la visualizzazione inline

Nel notebook, aggiungi ed esegui:

```python
import matplotlib.pyplot as plt

%matplotlib inline
```

Se `%matplotlib inline` dà errore, prova semplicemente senza quella riga: in molte versioni moderne di Jupyter non è più strettamente necessaria.

**Checklist**
- [ ] Ho importato `matplotlib.pyplot as plt`
- [ ] Niente errori nell’import

---

### 2. Istogramma dei tempi di completamento

Assicurati che `completion_minutes_by_convoy` esista (dal Giorno 3).  
Aggiungi ed esegui:

```python
if len(completion_minutes_by_convoy) > 0:
    plt.figure()
    plt.hist(completion_minutes_by_convoy, bins=10)
    plt.xlabel("Minuto di completamento")
    plt.ylabel("Numero di convogli")
    plt.title("Distribuzione dei tempi di completamento dei convogli")
else:
    print("Nessun convoglio completato: impossibile creare l'istogramma.")
```

Dovresti vedere un istogramma con la distribuzione dei minuti di completamento.

**Checklist**
- [ ] Ho generato un istogramma dei tempi di completamento
- [ ] Il grafico appare nel notebook senza errori

---

### 3. Curva cumulativa dei convogli completati nel tempo

Costruiamo una serie temporale con il numero cumulativo di convogli completati per minuto.

Aggiungi ed esegui:

```python
if len(df_completed) > 0:
    # Conta quanti completamenti avvengono a ogni minuto
    completed_per_minute = (
        df_completed
        .groupby("minute")["convoy_id"]
        .nunique()
        .sort_index()
    )

    # Calcola il cumulativo
    cumulative_completed = completed_per_minute.cumsum()

    plt.figure()
    plt.step(cumulative_completed.index, cumulative_completed.values, where="post")
    plt.xlabel("Minuto")
    plt.ylabel("Convogli completati (cumulativo)")
    plt.title("Convogli completati nel tempo (cumulativo)")
else:
    print("Nessun convoglio completato: impossibile creare la curva cumulativa.")
```

**Checklist**
- [ ] Ho creato il grafico cumulativo dei convogli completati nel tempo
- [ ] Il grafico appare senza errori

---

### Fine Parte 1 (Giorni 1–4) – Checklist riassuntiva

- [ ] So avviare Jupyter Notebook dal progetto su Windows
- [ ] Ho creato il notebook `analisi_eventi_base.ipynb` dentro `notebooks`
- [ ] Riesco a generare un CSV di eventi con `python -m src.sim.main_sim`
- [ ] Carico il CSV nel notebook usando `pandas.read_csv`
- [ ] Calcolo KPI base (`n_convoys`, completati/non completati, tempi di completamento)
- [ ] Creo un istogramma dei tempi di completamento
- [ ] Creo una curva cumulativa dei convogli completati nel tempo

Quando queste caselle sono spuntate, puoi passare alla **Parte 2 della Fase 03** (`fase03_2.md`), dove sposterai la logica KPI in un **modulo Python riutilizzabile**, aggiungerai **test automatici** e un piccolo script da riga di comando.
