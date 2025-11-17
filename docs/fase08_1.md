# Fase 08 – Metriche & validazione modello rischio (Parte 1, Giorni 1–3, Windows)

> **Scopo Fase 08 (visione generale)**  
> Rendere il modello di rischio più **affidabile e controllato**, aggiungendo:
>
> - un **notebook di valutazione** per vedere come si comporta il modello,
> - metriche più serie (precision, recall, F1, AUC ROC),
> - analisi di diverse **soglie di rischio** per capire quando considerare “alto rischio”.
>
> In **Parte 1** lavorerai soprattutto da notebook, senza toccare ancora codice di produzione.

> **Prerequisiti**:
> - `data\processed\convoy_risk_dataset.csv` esiste (Fase 04),
> - `models\risk_model.pkl` esiste (Fase 05),
> - l’API e la UI non sono strettamente necessarie, ma dovrebbero funzionare.

---

## Struttura Fase 08 – Parte 1

- **Giorno 1** – Notebook `evaluate_risk_model.ipynb`: caricare dataset e modello, metriche base
- **Giorno 2** – Analisi più approfondita: AUC ROC, curve, confronto soglie
- **Giorno 3** – Tabella di confronto soglie e scelta di una soglia “predefinita”

---

## Giorno 1 – Notebook di valutazione `evaluate_risk_model.ipynb`

### Obiettivo del giorno
- Creare un notebook dedicato alla **valutazione del modello**,
- Caricare il dataset e il modello,
- Calcolare le **metriche di classificazione standard** su un train/test split semplice.

---

### 1. Avviare Jupyter Notebook

1. Apri **PowerShell** o **cmd**.
2. Vai nella cartella del progetto (sostituisci `TUO_UTENTE`):

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

4. Avvia Jupyter Notebook:

```bash
jupyter notebook
```

5. Nel browser, entra nella cartella `notebooks`.

**Checklist**
- [ ] Jupyter è avviato dal progetto
- [ ] Sono dentro la cartella `notebooks`

---

### 2. Creare il notebook `evaluate_risk_model.ipynb`

Nel browser (Jupyter):

1. Clicca su **New → Python 3 (ipykernel)**.
2. Rinomina il notebook in alto (clic sul titolo) in:
   - `evaluate_risk_model.ipynb`

Nella prima cella, inserisci e lancia:

```python
import sys
print(sys.version)
```

**Checklist**
- [ ] Ho creato il notebook `evaluate_risk_model.ipynb`
- [ ] Una prima cella stampa la versione di Python

---

### 3. Importare le librerie necessarie

In una nuova cella, scrivi e lancia:

```python
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
```

Se qualche import dà errore, controlla che i pacchetti siano nel `requirements.txt` e installati.

**Checklist**
- [ ] `pandas`, `joblib`, `sklearn.metrics`, `sklearn.model_selection` sono importabili

---

### 4. Caricare il dataset e il modello di rischio

Aggiungi una nuova cella:

```python
dataset_path = Path("../data/processed/convoy_risk_dataset.csv")
model_path = Path("../models/risk_model.pkl")

print("Dataset path:", dataset_path)
print("Model path:", model_path)

df = pd.read_csv(dataset_path)
model = joblib.load(model_path)
```

Poi un’altra cella per dare un’occhiata al dataset:

```python
df.head()
```

E una cella per vedere dimensioni e distribuzione della label:

```python
len(df), df["risk_label"].value_counts()
```

**Checklist**
- [ ] Il dataset viene caricato senza errori
- [ ] Il modello `risk_model.pkl` viene caricato senza errori
- [ ] Vedo qualche riga di esempio e la distribuzione di `risk_label`

---

### 5. Creare un train/test split manuale nel notebook

Userai le stesse feature minime del modello (es. `total_minutes` e `timestep_minutes`).

Aggiungi una cella:

```python
feature_cols = ["total_minutes", "timestep_minutes"]
label_col = "risk_label"

X = df[feature_cols].copy()
y = df[label_col].astype(int).copy()

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.3,
    random_state=42,
    stratify=y if y.nunique() > 1 else None,
)

X_train.shape, X_test.shape, y_train.shape, y_test.shape
```

**Checklist**
- [ ] Ho definito `X`, `y` correttamente
- [ ] Ho creato `X_train`, `X_test`, `y_train`, `y_test` senza errori

---

### 6. Calcolare le metriche di base sul test set

Anche se il modello è già addestrato, puoi comunque usarlo per predire sul test set.

Aggiungi una cella:

```python
y_pred = model.predict(X_test)

print("Confusion matrix:")
print(confusion_matrix(y_test, y_pred))

print()
print("Classification report:")
print(classification_report(y_test, y_pred, digits=3))
```

> Non ti preoccupare se i numeri non sono “perfetti”: qui l’obiettivo è **capire il comportamento**, non ottimizzare al massimo le prestazioni.

**Checklist (fine Giorno 1)**
- [ ] Ho ottenuto una confusion matrix
- [ ] Ho ottenuto un classification report (precision, recall, f1 per ciascuna classe)
- [ ] Capisco approssimativamente se il modello tende a sbagliare più i “positivi” o i “negativi”

---

## Giorno 2 – Analisi ROC, curve e confronto soglie

### Obiettivo del giorno
- Calcolare e visualizzare la **ROC curve**,
- Calcolare l’AUC,
- Esplorare come cambiano le metriche al variare della **soglia di decisione** (non solo 0.5).

---

### 1. Calcolare le probabilità invece delle classi secche

In una nuova cella del notebook, calcola le probabilità di classe 1:

```python
from sklearn.metrics import roc_curve, roc_auc_score

# Probabilità che risk_label == 1 (classe "a rischio")
y_proba = model.predict_proba(X_test)[:, 1]

len(y_proba), y_proba[:10]
```

**Checklist**
- [ ] `y_proba` è un array della stessa lunghezza di `y_test`
- [ ] I primi valori di `y_proba` hanno senso (numeri tra 0 e 1)

---

### 2. Calcolare ROC curve e AUC

Aggiungi una cella:

```python
fpr, tpr, thresholds = roc_curve(y_test, y_proba)
auc = roc_auc_score(y_test, y_proba)

auc
```

`auc` sarà un numero tra 0 e 1 (più vicino a 1 significa modello migliore nel distinguere le classi).

**Checklist**
- [ ] Ho ottenuto `fpr`, `tpr` e `thresholds`
- [ ] Ho calcolato un valore di `auc`

---

### 3. Visualizzare la ROC curve

Per vedere la ROC curve, importa `matplotlib` e disegna il grafico.

In una nuova cella:

```python
import matplotlib.pyplot as plt

plt.figure()
plt.plot(fpr, tpr, label=f"ROC (AUC = {auc:.3f})")
plt.plot([0, 1], [0, 1], "k--", label="Random")
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC curve – modello di rischio convoglio")
plt.legend()
plt.grid(True)
plt.show()
```

> Non serve che il grafico sia “perfetto”: l’importante è che visualizzi come si comporta il modello.

**Checklist**
- [ ] Vedo una ROC curve con una linea principale e la diagonale “Random”
- [ ] Ho un’idea se la curva è “sopra” la diagonale (meglio di caso random)

---

### 4. Esplorare diverse soglie di rischio

Ora vogliamo vedere come cambiano **precision e recall** quando **non** usiamo la soglia standard di 0.5, ma ad esempio: 0.3, 0.5, 0.7.

Aggiungi una cella:

```python
from sklearn.metrics import precision_score, recall_score, f1_score

thresholds_to_try = [0.3, 0.5, 0.7]

rows = []

for thr in thresholds_to_try:
    y_pred_thr = (y_proba >= thr).astype(int)

    prec = precision_score(y_test, y_pred_thr, zero_division=0)
    rec = recall_score(y_test, y_pred_thr, zero_division=0)
    f1 = f1_score(y_test, y_pred_thr, zero_division=0)

    rows.append(
        {
            "threshold": thr,
            "precision": prec,
            "recall": rec,
            "f1": f1,
        }
    )

metrics_df = pd.DataFrame(rows)
metrics_df
```

**Checklist**
- [ ] Ho una tabella `metrics_df` con colonne `threshold`, `precision`, `recall`, `f1`
- [ ] Vedo come cambiano precision/recall al variare della soglia

---

### 5. Visualizzare l’andamento di precision & recall in funzione della soglia

Per avere un’idea più visiva, puoi testare molte soglie tra 0 e 1.

Aggiungi una cella:

```python
thresholds_grid = [round(x, 2) for x in list(pd.np.linspace(0.0, 1.0, 21))]  # 0.00, 0.05, ..., 1.00

rows = []
for thr in thresholds_grid:
    y_pred_thr = (y_proba >= thr).astype(int)
    prec = precision_score(y_test, y_pred_thr, zero_division=0)
    rec = recall_score(y_test, y_pred_thr, zero_division=0)
    rows.append({"threshold": thr, "precision": prec, "recall": rec})

thr_df = pd.DataFrame(rows)
thr_df.head()
```

Poi una cella per il grafico:

```python
plt.figure()
plt.plot(thr_df["threshold"], thr_df["precision"], label="Precision")
plt.plot(thr_df["threshold"], thr_df["recall"], label="Recall")
plt.xlabel("Soglia di decisione")
plt.ylabel("Valore metrica")
plt.title("Precision e Recall in funzione della soglia")
plt.legend()
plt.grid(True)
plt.show()
```

> In alcune versioni di pandas l’alias `pd.np` è deprecato; se ti dà errore, usa:
> ```python
> import numpy as np
> thresholds_grid = [round(x, 2) for x in np.linspace(0.0, 1.0, 21)]
> ```

**Checklist (fine Giorno 2)**
- [ ] Ho visto l’AUC ROC del modello
- [ ] Ho una tabella con precision/recall per alcune soglie (0.3, 0.5, 0.7)
- [ ] Ho un grafico con precision e recall in funzione della soglia

---

## Giorno 3 – Tabella confronto soglie & scelta soglia “predefinita”

### Obiettivo del giorno
- Fare una **tabella di confronto** tra soglie candidate,
- Scegliere una soglia “default” che userai in CLI, API e UI nelle fasi successive,
- Annotare nel notebook (e sul README) **perché** hai scelto quella soglia.

---

### 1. Tabella pulita di soglie candidate

Decidi quali soglie vuoi considerare davvero come candidate (es. 0.3, 0.4, 0.5, 0.6).

Aggiungi una cella:

```python
candidate_thresholds = [0.3, 0.4, 0.5, 0.6]

rows = []
for thr in candidate_thresholds:
    y_pred_thr = (y_proba >= thr).astype(int)
    prec = precision_score(y_test, y_pred_thr, zero_division=0)
    rec = recall_score(y_test, y_pred_thr, zero_division=0)
    f1 = f1_score(y_test, y_pred_thr, zero_division=0)

    rows.append(
        {
            "threshold": thr,
            "precision": prec,
            "recall": rec,
            "f1": f1,
        }
    )

candidate_df = pd.DataFrame(rows).sort_values("threshold")
candidate_df
```

Osserva la tabella e prova a ragionare:

- Soglie più basse → di solito **più recall**, meno precision.
- Soglie più alte → di solito **più precision**, meno recall.

**Checklist**
- [ ] Ho una tabella `candidate_df` che confronta soglie diverse
- [ ] Ho un’idea di quali soglie sembrano più “sensate” per questo modello

---

### 2. Scegliere una soglia “default”

Ora scegli una soglia che ti sembra un buon compromesso.  
Puoi usare dei criteri semplici, ad esempio:

- soglia con **F1 più alto**, oppure
- soglia con recall sopra un certo valore (es. 0.7) ma buona precision, oppure
- soglia che “ti sembra” ragionevole guardando la tabella.

Aggiungi una cella per evidenziare la soglia con F1 massimo:

```python
best_row = candidate_df.sort_values("f1", ascending=False).iloc[0]
best_row
```

Da qui puoi leggere la soglia con F1 massimo, ad esempio:

```python
best_threshold = float(best_row["threshold"])
best_threshold
```

**Checklist**
- [ ] Ho individuato una soglia “migliore” secondo un criterio (es. F1 massimo)
- [ ] Ho salvato la soglia in una variabile `best_threshold`

---

### 3. Annotare la scelta nel notebook (importante!)

Aggiungi una **cella Markdown** (non di codice) alla fine del notebook con un testo tipo:

```markdown
### Scelta soglia di rischio predefinita

Dalla tabella `candidate_df` abbiamo confrontato le soglie candidate 0.3, 0.4, 0.5 e 0.6.

- Soglia X: precision = ..., recall = ..., f1 = ...
- ...

Abbiamo scelto come **soglia di rischio predefinita**:

- `risk_threshold_default = X`

perché:
- [motivo 1: es. buon compromesso tra precision e recall]
- [motivo 2: es. preferiamo evitare falsi negativi, quindi accettiamo qualche falso positivo in più]
```

Sostituisci **X** e i motivi con i valori reali che vedi nel tuo notebook.

Questa decisione sarà utile nella **Parte 2** della Fase 08, quando andrai a:

- aggiungere `risk_threshold_default` nel codice Python (CLI, API, UI),
- aggiornare un po’ la logica che evidenzia i convogli ad alto rischio.

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] Ho creato il notebook `evaluate_risk_model.ipynb`
- [ ] Ho calcolato classification report e confusion matrix
- [ ] Ho calcolato AUC ROC e visto la relativa curva
- [ ] Ho analizzato precision/recall per più soglie
- [ ] Ho scelto una **soglia di rischio predefinita** e spiegato la scelta in una cella Markdown

A questo punto sei pronto per la **Parte 2** della Fase 08 (`fase08_2.md`), in cui:

- introdurrai un piccolo modulo Python per le soglie,
- aggiornerai CLI, API e UI per usare la soglia “default”,
- aggiungerai test di coerenza per il valore di soglia scelto.
