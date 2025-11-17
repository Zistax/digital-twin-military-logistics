# Fase 04 – Dataset rischio convoglio & primo modello (Parte 1, Giorni 1–4, Windows)

> **Scopo Fase 04 (visione generale)**  
> Preparare un **dataset per il rischio convoglio** a partire dai log eventi del simulatore e arrivare, alla fine della fase, a un **primo modello di rischio molto semplice** addestrato in locale.
>
> In **Parte 1 (questo file)** ti concentri solo sul dataset, usando un notebook.

In questa Parte 1 farai:

- **Giorno 1** – Generare più log di simulazione (CSV) con scenari diversi
- **Giorno 2** – Creare il notebook `build_risk_dataset.ipynb` e combinare più CSV
- **Giorno 3** – Costruire un dataset a livello di convoglio (una riga per convoglio)
- **Giorno 4** – Salvare il dataset in `data\processed` e fare controlli base

> Assicurati di avere funzionante la Fase 02–03:
> - `python -m src.sim.main_sim` genera CSV in `data\raw`
> - `python -m src.sim.analyze_last_run` (Fase 03) è in grado di calcolare KPI di base

---

## Giorno 1 – Generare più log di simulazione (scenari diversi)

### Obiettivo del giorno
Creare almeno **3–5 file CSV** di simulazione in `data\raw`, con **configurazioni diverse**, per avere un minimo di varietà nel dataset.

Idealmente:

- Alcune simulazioni in cui **tutti i convogli completano** la missione
- Almeno una simulazione in cui **alcuni convogli NON completano** (durata troppo breve)

> Nota: nel tuo simulatore attuale, i convogli avanzano di una quota fissa ad ogni passo.
> Se la simulazione dura troppo poco (pochi minuti totali), è possibile che **non arrivino a completare**.

---

### 1. Attivare ambiente e lanciare più simulazioni

1. Apri **PowerShell** o **cmd**.
2. Vai nella cartella del progetto (sostituisci `TUO_UTENTE`):

```bash
cd C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico
```

3. Attiva l’ambiente virtuale `.venv`:

- PowerShell:
  ```bash
  .venv\Scripts\Activate.ps1
  ```
- cmd:
  ```bat
  .venv\Scripts\activate.bat
  ```

4. Lancia il simulatore più volte, cambiando i parametri:

```bash
python -m src.sim.main_sim
```

Ad ogni esecuzione:

- ti verrà chiesto:
  - Durata totale simulazione (minuti)
  - Durata di ogni passo (minuti)
  - Numero di convogli
  - Capacità del deposito

- ti verrà mostrato il percorso del CSV creato, ad es.:  
  `Log eventi salvato in: data\raw\sim_events_20250101_153000.csv`

---

### 2. Suggerimenti per le configurazioni

Prova ad esempio:

1. **Simulazione “normale”** (tutti completano):
   - Durata totale: `120`
   - Timestep: `10`
   - Numero convogli: `5`
   - Capacità deposito: `2`

2. **Simulazione più lunga** (tutti completano):
   - Durata totale: `240`
   - Timestep: `10`
   - Numero convogli: `8`
   - Capacità deposito: `3`

3. **Simulazione troppo breve** (possibile che alcuni non completino):
   - Durata totale: `30`
   - Timestep: `10`
   - Numero convogli: `5`
   - Capacità deposito: `2`

4. **Altre varianti** (facoltative):
   - Durata totale: `60`
   - Timestep: `15`
   - Numero convogli: `3` o `10`

> Non devi usare esattamente questi numeri, ma l’importante è che tu abbia:
> - almeno una simulazione con convogli che **non completano**.

---

### 3. Verificare i file in `data\raw`

Dopo aver lanciato 3–5 simulazioni, apri **Esplora File** e vai in:

```text
C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico\data\raw
```

Dovresti vedere vari file:

```text
sim_events_2025XXXXXXXX_XXXXXX.csv
sim_events_2025XXXXXXXX_XXXXXX.csv
...
```

**Checklist (fine Giorno 1)**

- [ ] Ho eseguito il simulatore con **almeno 3–5 configurazioni diverse**
- [ ] In `data\raw` ci sono più file `sim_events_*.csv`
- [ ] So quale configurazione ho usato per le simulazioni “normali” e “brevi”

---

## Giorno 2 – Notebook `build_risk_dataset.ipynb` e unione dei CSV

### Obiettivo del giorno
- Creare il notebook `build_risk_dataset.ipynb`
- Caricare **tutti** i file `sim_events_*.csv` da `data\raw`
- Aggiungere una colonna `run_id` che identifichi la simulazione (derivata dal nome file)
- Unire tutti gli eventi in un unico DataFrame

---

### 1. Avviare Jupyter Notebook (come già fatto in Fase 03)

Nel terminale, dalla cartella del progetto, con `.venv` attivo:

```bash
jupyter notebook
```

Nel browser:

1. Entra nella cartella `notebooks`.
2. Clicca su **New → Python 3 (ipykernel)**.
3. Rinomina il notebook in alto (clic sul titolo) in:
   - `build_risk_dataset.ipynb`

**Checklist**
- [ ] Jupyter è avviato
- [ ] Ho creato `build_risk_dataset.ipynb` nella cartella `notebooks`

---

### 2. Import base (pandas e pathlib)

Nella prima cella del notebook, scrivi e esegui:

```python
from pathlib import Path

import pandas as pd
```

**Checklist**
- [ ] `import pandas as pd` funziona senza errori

---

### 3. Trovare tutti i CSV in `data/raw`

Aggiungi una nuova cella e scrivi:

```python
raw_dir = Path("../data/raw")
csv_files = sorted(raw_dir.glob("sim_events_*.csv"))
csv_files
```

Esegui la cella.  
Dovresti vedere una lista di percorsi (`[WindowsPath('...'), ...]`).

Se la lista è vuota:

- controlla di aver scritto correttamente `../data/raw`
- controlla di aver lanciato le simulazioni nel Giorno 1

**Checklist**
- [ ] `csv_files` contiene una lista di file `sim_events_*.csv`

---

### 4. Caricare e unire tutti i CSV con una colonna `run_id`

Aggiungi una nuova cella:

```python
all_dfs = []

for csv_path in csv_files:
    # run_id ricavato dal nome del file, es. "sim_events_20250101_153000"
    run_id = csv_path.stem  # nome file senza estensione

    df = pd.read_csv(csv_path)
    df["run_id"] = run_id

    all_dfs.append(df)

len(all_dfs)
```

Esegui. Dovresti vedere il numero di file caricati (3, 4, 5, ...).

Poi unisci tutto in un unico DataFrame:

```python
df_all = pd.concat(all_dfs, ignore_index=True)
df_all.head()
```

**Checklist (fine Giorno 2)**

- [ ] Ho trovato tutti i file `sim_events_*.csv` con `Path.glob`
- [ ] Ho creato `df_all` con **tutti** gli eventi di tutte le simulazioni
- [ ] `df_all.head()` mostra le prime righe, con in più la colonna `run_id`

---

## Giorno 3 – Costruire il dataset per convoglio (una riga per convoglio)

### Obiettivo del giorno
Trasformare `df_all` (una riga = un evento) in un dataset con **una riga per convoglio**, che contenga:

- identificatore di run (`run_id`)
- identificatore convoglio (`convoy_id`)
- `total_minutes` della simulazione (ricavato da `minute` max)
- `timestep_minutes` approssimato
- `is_completed` (True/False)
- `risk_label` (0 se convoglio completato, 1 se non completato)

> In questa fase, consideriamo **convoglio “a rischio” = convoglio che NON completa la missione**.  
> Quindi `risk_label = 1` significa “convoglio problematico”.

---

### 1. Controllare le colonne disponibili

Nel notebook, aggiungi una cella e esegui:

```python
df_all.columns.tolist()
```

Dovresti vedere una lista con colonne tipo:

- `event_type`
- `convoy_id`
- `minute`
- `step_index`
- `progress`
- `run_id`
- (eventuali altre, se aggiunte)

**Checklist**
- [ ] Confermo che esistono almeno `event_type`, `convoy_id`, `minute`, `run_id`

---

### 2. Calcolare meta-informazioni per ogni run (`run_id`)

Aggiungi una cella per creare un DataFrame con metadati per simulazione:

```python
# Calcoliamo, per ogni run_id, il minuto massimo (usato come total_minutes)
run_meta = (
    df_all
    .groupby("run_id")["minute"]
    .max()
    .reset_index()
    .rename(columns={"minute": "total_minutes"})
)

run_meta
```

Facoltativo: calcolare anche un timestep approssimativo per run:

```python
def estimate_timestep_minutes(df_run: pd.DataFrame) -> int:
    unique_minutes = sorted(df_run["minute"].unique())
    if len(unique_minutes) < 2:
        return unique_minutes[0] if unique_minutes else 0
    # differenza tra i primi due valori distinti
    return int(unique_minutes[1] - unique_minutes[0])


timestep_list = []

for run_id, df_run in df_all.groupby("run_id"):
    ts = estimate_timestep_minutes(df_run)
    timestep_list.append({"run_id": run_id, "timestep_minutes": ts})

run_timestep = pd.DataFrame(timestep_list)
run_timestep
```

Ora unisci i due DataFrame di meta-informazioni:

```python
run_info = pd.merge(run_meta, run_timestep, on="run_id", how="left")
run_info
```

**Checklist**
- [ ] Ho creato `run_meta` con `run_id` e `total_minutes`
- [ ] Ho creato `run_timestep` con `run_id` e `timestep_minutes`
- [ ] Ho unito in `run_info`

---

### 3. Creare una tabella convogli con label di rischio

Ora costruiamo il dataset principale.

Aggiungi una cella con:

```python
rows = []

grouped = df_all.groupby(["run_id", "convoy_id"])

for (run_id, convoy_id), group in grouped:
    # meta info per questa run
    info = run_info[run_info["run_id"] == run_id].iloc[0]
    total_minutes = int(info["total_minutes"])
    timestep_minutes = int(info["timestep_minutes"])

    # convoglio completato?
    df_completed = group[group["event_type"] == "convoy_completed"]
    is_completed = len(df_completed) > 0

    # per ora non usiamo il minuto di completamento come feature,
    # ma potresti aggiungerlo se ti serve
    if is_completed:
        completion_minute = int(df_completed["minute"].min())
    else:
        completion_minute = None

    # Definizione semplice di rischio:
    # - 0 = convoglio completato
    # - 1 = convoglio non completato
    risk_label = 0 if is_completed else 1

    row = {
        "run_id": run_id,
        "convoy_id": int(convoy_id),
        "total_minutes": total_minutes,
        "timestep_minutes": timestep_minutes,
        "is_completed": is_completed,
        "completion_minute": completion_minute,
        "risk_label": risk_label,
    }

    rows.append(row)

df_convoys = pd.DataFrame(rows)
df_convoys.head()
```

**Checklist**
- [ ] Ho creato una lista `rows` e poi un DataFrame `df_convoys`
- [ ] `df_convoys.head()` mostra una riga per `run_id` + `convoy_id`

---

### 4. Controlli veloci sul dataset convogli

Aggiungi ed esegui qualche cella di controllo:

```python
# Numero totale di convogli nel dataset
len(df_convoys)
```

```python
# Distribuzione dell'etichetta di rischio
df_convoys["risk_label"].value_counts()
```

```python
# Verifica se ci sono convogli non completati
df_convoys["is_completed"].value_counts()
```

```python
# Quali run_id hanno convogli a rischio (risk_label=1)
df_convoys[df_convoys["risk_label"] == 1]["run_id"].value_counts()
```

Se **non** hai alcun convoglio con `risk_label = 1`, significa che in tutte le simulazioni tutti i convogli hanno completato. In questo caso:

- torna al **Giorno 1**
- lancia alcune simulazioni con **durata totale troppo breve** rispetto all’avanzamento dei convogli
- rigenera il notebook da zero oppure aggiungi nuove simulazioni e ripeti i passaggi per aggiornare `df_all` e `df_convoys`

**Checklist (fine Giorno 3)**

- [ ] `df_convoys` esiste e ha le colonne `run_id`, `convoy_id`, `total_minutes`, `timestep_minutes`, `is_completed`, `completion_minute`, `risk_label`
- [ ] Ho controllato la distribuzione di `risk_label`
- [ ] Ci sono **sia 0 che 1** in `risk_label` (almeno qualche convoglio a rischio)

---

## Giorno 4 – Salvare il dataset in `data\processed` e controlli finali

### Obiettivo del giorno
- Salvare `df_convoys` in `data\processed` come CSV riutilizzabile
- Fare qualche ultimo controllo per sicurezza

---

### 1. Creare (se serve) la cartella `data\processed`

Dalla cartella del progetto, se non l’hai già creata:

```bash
mkdir data\processed
```

Se la cartella esiste già (dalla Fase 02–03), il comando può dare errore o dire che esiste già; non è un problema.

**Checklist**
- [ ] `data\processed` esiste nella cartella del progetto

---

### 2. Salvare il dataset convogli in CSV

Nel notebook `build_risk_dataset.ipynb`, aggiungi una cella:

```python
output_path = "../data/processed/convoy_risk_dataset.csv"
df_convoys.to_csv(output_path, index=False)
output_path
```

Esegui la cella.  
Dovresti vedere il percorso relativo del file.

In Esplora File, controlla:

```text
C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico\data\processed\convoy_risk_dataset.csv
```

Apri il CSV (anche solo in Blocco Note o Excel) e verifica che:

- ci siano più righe (una per convoglio)
- ci siano le colonne viste prima

**Checklist**
- [ ] Ho salvato `convoy_risk_dataset.csv` in `data\processed`
- [ ] Il file si apre e contiene le colonne attese

---

### 3. Riassunto finale di Parte 1 (pronto per Parte 2)

Nel notebook, puoi aggiungere una cella finale con un piccolo riepilogo:

```python
print("Righe dataset:", len(df_convoys))
print("Distribuzione risk_label:")
print(df_convoys["risk_label"].value_counts())
```

Se tutto ha senso, la Parte 1 è completa.

**Checklist (fine Parte 1 – Giorni 1–4)**

- [ ] Ho generato più file CSV eventi in `data\raw` con varie configurazioni
- [ ] Ho creato il notebook `build_risk_dataset.ipynb`
- [ ] Ho caricato e unito tutti i CSV in `df_all` con colonna `run_id`
- [ ] Ho costruito `df_convoys` (una riga per convoglio) con colonna `risk_label`
- [ ] Ho salvato `convoy_risk_dataset.csv` in `data\processed`
- [ ] Esistono sia convogli “normali” (`risk_label = 0`) sia convogli “a rischio” (`risk_label = 1`)

Quando tutte queste caselle sono spuntate, puoi passare alla **Parte 2 della Fase 04** (`fase04_2.md`), dove sposterai la logica in moduli Python riutilizzabili (`src\ml`) e addestrerai un **primo modello di rischio semplice**.
