# Fase 04 – Dataset rischio convoglio & primo modello (Parte 2, Giorni 5–8, Windows)

> **Scopo Parte 2**  
> Spostare la logica di costruzione del dataset in **moduli Python riutilizzabili** e addestrare un **primo modello di rischio semplice** (es. Logistic Regression) usando scikit-learn.

In questa Parte 2 farai:

- **Giorno 5** – Aggiungere scikit-learn ai requisiti e creare `src\ml\dataset.py`
- **Giorno 6** – Creare lo script `src\ml\train_risk_model.py` (addestramento modello)
- **Giorno 7** – Aggiungere test per il dataset e il modello
- **Giorno 8** – Esecuzione completa (dataset + training) e commit Git fine Fase 04

> Assicurati che `data\processed\convoy_risk_dataset.csv` esista (creato in `fase04_1.md`).

---

## Giorno 5 – Aggiungere scikit-learn e creare `src\ml\dataset.py`

### Obiettivo del giorno
- Aggiungere **scikit-learn** ai pacchetti del progetto
- Creare il modulo `src\ml\dataset.py` per caricare il dataset e fare alcuni controlli

---

### 1. Aggiornare `requirements.txt` con scikit-learn

1. Apri `requirements.txt` nella radice del progetto.
2. Aggiungi una riga (se non esiste ancora):

```txt
scikit-learn
```

3. Salva il file.

4. Nel terminale (con `.venv` attivo), dalla cartella del progetto:

```bash
pip install -r requirements.txt
```

Attendi che l’installazione finisca.

**Checklist**
- [x] `requirements.txt` contiene `scikit-learn`
- [x] `pip install -r requirements.txt` è andato a buon fine

---

### 2. Creare la cartella `models` (per salvare il modello più avanti)

Dalla cartella del progetto (cmd/PowerShell):

```bash
mkdir models
```

Se esiste già, nessun problema.

**Checklist**
- [x] La cartella `models` esiste nella root del progetto

---

### 3. Creare `src\ml\dataset.py`

1. Apri **VS Code**.
2. Nella barra laterale, espandi `src` → `ml`.
3. Crea un file chiamato `dataset.py`.
4. Inserisci il seguente contenuto:

```python
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd
from sklearn.model_selection import train_test_split


def load_convoy_risk_dataset(
    csv_path: str | Path = "data/processed/convoy_risk_dataset.csv",
) -> pd.DataFrame:
    """Carica il dataset dei convogli da un file CSV."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"File dataset non trovato: {csv_path}")

    df = pd.read_csv(csv_path)
    return df


def split_features_labels(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    label_col: str = "risk_label",
    test_size: float = 0.3,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Divide il dataset in train/test per un problema di classificazione binaria."""
    if label_col not in df.columns:
        raise ValueError(f"La colonna label '{label_col}' non è presente nel DataFrame.")

    if feature_cols is None:
        # Usiamo un set minimo di feature numeriche (puoi estenderlo in futuro)
        feature_cols = ["total_minutes", "timestep_minutes"]

    for col in feature_cols:
        if col not in df.columns:
            raise ValueError(f"La colonna di feature '{col}' non è presente nel DataFrame.")

    X = df[feature_cols].copy()
    y = df[label_col].astype(int).copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y if y.nunique() > 1 else None,
    )

    return X_train, X_test, y_train, y_test
```

5. Salva il file.

**Checklist (fine Giorno 5)**

- [x] `scikit-learn` è installato nel tuo ambiente `.venv`
- [x] Esiste `src\ml\dataset.py`
- [x] Le funzioni `load_convoy_risk_dataset` e `split_features_labels` sono definite

---

## Giorno 6 – Script di training `train_risk_model.py`

### Obiettivo del giorno
Creare lo script `src\ml\train_risk_model.py` che:

- carica il dataset `convoy_risk_dataset.csv`
- divide in train/test
- addestra un modello semplice (Logistic Regression)
- stampa metriche base
- salva il modello in `models\risk_model.pkl`

---

### 1. Creare il file `src\ml\train_risk_model.py`

1. In VS Code, sotto `src\ml`, crea il file `train_risk_model.py`.
2. Inserisci il seguente contenuto:

```python
from __future__ import annotations

from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

from .dataset import load_convoy_risk_dataset, split_features_labels


def train_risk_model(
    dataset_path: str | Path = "data/processed/convoy_risk_dataset.csv",
    model_path: str | Path = "models/risk_model.pkl",
) -> None:
    """Addestra un modello di rischio semplice e lo salva su disco."""
    print("Carico il dataset...")
    df = load_convoy_risk_dataset(dataset_path)

    print("Divido in train/test...")
    X_train, X_test, y_train, y_test = split_features_labels(df)

    print("Forma dei dataset:")
    print(f"  X_train: {X_train.shape}")
    print(f"  X_test:  {X_test.shape}")

    # Modello molto semplice: Logistic Regression con parametri di default
    print("Addestro il modello (Logistic Regression)...")
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    print("Valuto il modello sul test set...")
    y_pred = model.predict(X_test)

    print("=== Confusion Matrix ===")
    print(confusion_matrix(y_test, y_pred))

    print()
    print("=== Classification Report ===")
    print(classification_report(y_test, y_pred, digits=3))

    # Salvataggio del modello
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)

    print()
    print(f"Modello salvato in: {model_path}")


def main() -> None:
    train_risk_model()


if __name__ == "__main__":
    main()
```

3. Salva il file.

> Nota: `joblib` viene installato automaticamente come dipendenza di scikit-learn nella maggior parte dei casi.  
> Se non lo fosse, puoi aggiungere `joblib` al `requirements.txt` e reinstallare.

---

### 2. Eseguire lo script di training dal terminale

Nel terminale (con `.venv` attivo), dalla cartella del progetto:

```bash
python -m src.ml.train_risk_model
```

Se tutto va bene, dovresti vedere:

- messaggi di caricamento dataset
- divisione train/test
- confusion matrix
- classification report
- percorso del file modello salvato (es. `models\risk_model.pkl`)

**Checklist (fine Giorno 6)**

- [x] `src\ml\train_risk_model.py` esiste
- [x] `python -m src.ml.train_risk_model` gira senza errori
- [x] In `models` compare un file `risk_model.pkl`

---

## Giorno 7 – Test automatici per dataset e training

### Obiettivo del giorno
- Aggiungere test per le funzioni di `dataset.py`
- Aggiungere almeno un test di base per `train_risk_model` (che giri su un piccolo dataset finto)

---

### 1. Test per `split_features_labels` su un dataset finto

1. In VS Code, nella cartella `tests`, crea il file `test_ml_dataset.py`.
2. Inserisci questo contenuto:

```python
import pandas as pd

from src.ml.dataset import split_features_labels


def test_split_features_labels_basic():
    """Verifica che la funzione divida correttamente X e y."""
    data = {
        "total_minutes": [30, 60, 120, 120],
        "timestep_minutes": [10, 10, 10, 20],
        "risk_label": [1, 0, 0, 1],
    }
    df = pd.DataFrame(data)

    X_train, X_test, y_train, y_test = split_features_labels(df, test_size=0.5, random_state=0)

    # Controlliamo le dimensioni
    assert len(X_train) + len(X_test) == len(df)
    assert len(y_train) + len(y_test) == len(df)

    # Verifichiamo che le colonne di X siano solo le feature numeriche
    assert list(X_train.columns) == ["total_minutes", "timestep_minutes"]
```

3. Salva il file.

**Checklist**
- [x] Esiste `tests\test_ml_dataset.py`
- [x] C’è almeno il test `test_split_features_labels_basic`

---

### 2. (Opzionale ma utile) Test per `train_risk_model`

Per non rendere il test troppo pesante, possiamo:

- creare un piccolo CSV temporaneo in `data\processed` solo per il test
- chiamare `train_risk_model` con percorsi specifici
- verificare che il file modello venga creato

1. In VS Code, sempre in `tests`, puoi aggiungere in `test_ml_dataset.py` un secondo test, oppure creare un file separato `test_train_risk_model.py`.  
   Esempio (in `test_train_risk_model.py`):

```python
from pathlib import Path

import pandas as pd

from src.ml.train_risk_model import train_risk_model


def test_train_risk_model_creates_file(tmp_path):
    """Verifica che train_risk_model crei un file modello su un dataset finto."""
    # Creiamo un piccolo dataset finto
    data = {
        "total_minutes": [30, 60, 120, 120],
        "timestep_minutes": [10, 10, 10, 20],
        "risk_label": [1, 0, 0, 1],
    }
    df = pd.DataFrame(data)

    # Percorsi temporanei
    dataset_path = tmp_path / "convoy_risk_dataset_test.csv"
    model_path = tmp_path / "risk_model_test.pkl"

    df.to_csv(dataset_path, index=False)

    # Eseguiamo il training
    train_risk_model(dataset_path=dataset_path, model_path=model_path)

    # Verifichiamo che il file modello sia stato creato
    assert model_path.exists()
```

2. Salva il file.

> Nota: `tmp_path` è una fixture di pytest che crea una cartella temporanea per ogni test.

**Checklist**
- [x] Esiste un test che verifica la creazione di un file modello con `train_risk_model`

---

### 3. Eseguire `pytest` per tutti i test

Nel terminale (con `.venv` attivo), dalla cartella del progetto:

```bash
pytest
```

Assicurati che:

- passino i test di Fase 01–02–03 (dummy, simulator, metrics)
- passino i test nuovi di Fase 04 (dataset e training)

**Checklist (fine Giorno 7)**

- [x] `pytest` gira senza errori
- [x] Tutti i test, inclusi quelli di `test_ml_dataset.py` e `test_train_risk_model.py`, passano

---

## Giorno 8 – Esecuzione completa e commit Git di fine Fase 04

### Obiettivo del giorno
- Verificare l’intera catena:
  - simulazione → CSV eventi → dataset convogli → training modello
- Fare un **commit Git** con la Fase 04 completata

---

### 1. Pipeline manuale end-to-end (consigliata)

1. Genera una o più simulazioni (se vuoi aggiornare i dati):

```bash
python -m src.sim.main_sim
```

2. (Opzionale) Analizza l’ultima simulazione:

```bash
python -m src.sim.analyze_last_run
```

3. Ricostruisci il dataset convogli (dal notebook `build_risk_dataset.ipynb`):
   - aggiorna `df_all` con tutti i CSV
   - rigenera `df_convoys`
   - risalva `data\processed\convoy_risk_dataset.csv`

4. Allena il modello:

```bash
python -m src.ml.train_risk_model
```

**Checklist**
- [x] Sono riuscito a rifare l’intera pipeline senza errori
- [x] Ho un nuovo `convoy_risk_dataset.csv` aggiornato
- [x] Ho un nuovo `models\risk_model.pkl` aggiornato

---

### 2. Commit Git di fine Fase 04

Nel terminale, dalla cartella del progetto:

```bash
git status
```

Dovresti vedere i file nuovi/modificati (es. in `src/ml/`, `tests/`, `requirements.txt`).

1. Aggiungi i file:

```bash
git add .
```

2. Crea un commit con un messaggio chiaro, ad esempio:

```bash
git commit -m "Fase 04: dataset rischio convoglio e primo modello di rischio"
```

3. Verifica che il working tree sia pulito:

```bash
git status
```

Dovresti vedere: `nothing to commit, working tree clean`.

**Checklist (fine Giorno 8)**

- [ ] Pipeline simulazione → dataset → modello testata end-to-end
- [ ] `pytest` passa
- [ ] Ho creato un commit Git per la Fase 04

---

## Fine Fase 04 – Criteri di completamento

La Fase 04 è completata quando:

- [ ] Esiste `data\processed\convoy_risk_dataset.csv` con convogli etichettati (`risk_label` 0/1)
- [ ] Esistono i file in `src\ml`:
  - `dataset.py`
  - `train_risk_model.py`
- [ ] Esistono i test:
  - `tests\test_ml_dataset.py`
  - (opzionale) `tests\test_train_risk_model.py`
- [ ] Posso eseguire `python -m src.ml.train_risk_model` e ottenere un file `models\risk_model.pkl`
- [ ] Tutti i test `pytest` passano
- [ ] Ho fatto il commit Git di fine Fase 04

Quando questi punti sono veri, hai:

- un **simulatore base**,
- log eventi strutturati,
- un **dataset di rischio convoglio**,
- un **primo modello di rischio** addestrato e salvato.

Nelle fasi successive potrai migliorare sia il simulatore (più realismo, più feature) sia il modello (feature engineering, modelli più complessi, valutazioni più avanzate).
