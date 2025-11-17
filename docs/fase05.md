# Fase 05 – Modulo di prediction & CLI rischio convoglio (Windows, Giorni 1–4)

> **Scopo Fase 05**  
> Aggiungere un **modulo di prediction** che carica il modello di rischio addestrato e un **programma da riga di comando** (CLI) che ti permette di:
>
> - inserire parametri di scenario (durata, timestep, numero convogli),
> - caricare automaticamente `models\risk_model.pkl`,
> - ottenere per ogni convoglio una **probabilità di rischio** (stima che il convoglio sia “problematico”).

Al termine della fase potrai lanciare un comando tipo:

```bash
python -m src.ml.predict_cli
```

e ottenere qualcosa del genere:

```text
Convoglio  Prob_rischio
1          0.23
2          0.23
3          0.23
...
```

> **Prerequisito importante**: Fase 04 completata, in particolare:
> - esiste `data\processed\convoy_risk_dataset.csv`
> - esiste `models\risk_model.pkl` generato da `python -m src.ml.train_risk_model`

---

## Struttura Fase 05

- **Giorno 1** – Creare il modulo `src\ml\predict.py` (funzioni di prediction)
- **Giorno 2** – Creare lo script da console `src\ml\predict_cli.py`
- **Giorno 3** – Aggiungere test per il modulo di prediction
- **Giorno 4** – Esecuzione completa (training + CLI) e commit Git

---

## Giorno 1 – Modulo `src\ml\predict.py`

### Obiettivo del giorno
Creare un modulo che si occupa di:

- caricare il modello da disco (`load_risk_model`)
- preparare i dati di input per la prediction (`prepare_convoy_features`)
- restituire le probabilità di rischio per i convogli (`predict_convoy_risk_proba`)

---

### 1. Attivare ambiente e aprire il progetto

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

4. Verifica che vedi `(.venv)` nel prompt.

**Checklist**
- [ ] Sono nella cartella del progetto
- [ ] L’ambiente `.venv` è attivo

---

### 2. Creare il file `src\ml\predict.py`

1. Apri **VS Code** e assicurati che la cartella `digital-twin-logistico` sia aperta.
2. Nella barra laterale, espandi `src` → `ml`.
3. Crea un nuovo file chiamato `predict.py`.
4. Inserisci il seguente contenuto:

```python
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd


def load_risk_model(model_path: str | Path = "models/risk_model.pkl"):
    """Carica il modello di rischio da file.

    Lancia FileNotFoundError se il file non esiste.
    """
    model_path = Path(model_path)

    if not model_path.exists():
        raise FileNotFoundError(f"File modello non trovato: {model_path}")

    model = joblib.load(model_path)
    return model


def prepare_convoy_features(
    total_minutes: int,
    timestep_minutes: int,
    n_convoys: int,
) -> pd.DataFrame:
    """Crea un DataFrame di feature per n_convoys convogli.

    In questa versione semplificata:
    - tutti i convogli hanno le stesse feature (total_minutes, timestep_minutes)
    - la differenza tra convogli non è ancora modellata (sarà migliorato in fasi successive)
    """
    if n_convoys <= 0:
        raise ValueError("n_convoys deve essere > 0")

    data = {
        "convoy_id": list(range(1, n_convoys + 1)),
        "total_minutes": [total_minutes] * n_convoys,
        "timestep_minutes": [timestep_minutes] * n_convoys,
    }

    df = pd.DataFrame(data)
    return df


def predict_convoy_risk_proba(
    model,
    total_minutes: int,
    timestep_minutes: int,
    n_convoys: int,
) -> pd.DataFrame:
    """Restituisce un DataFrame con la probabilità di rischio per ogni convoglio.

    Ritorna un DataFrame con colonne:
    - convoy_id
    - risk_proba (probabilità che risk_label == 1)
    """
    df_features = prepare_convoy_features(total_minutes, timestep_minutes, n_convoys)

    # Le colonne di feature devono corrispondere a quelle usate in training
    X = df_features[["total_minutes", "timestep_minutes"]].copy()

    # predict_proba restituisce un array shape (n_samples, 2)
    # colonna 0 = prob classe 0, colonna 1 = prob classe 1
    proba: np.ndarray = model.predict_proba(X)  # type: ignore[attr-defined]

    # Probabilità della classe "1" (convoglio a rischio)
    risk_proba = proba[:, 1]

    df_result = pd.DataFrame(
        {
            "convoy_id": df_features["convoy_id"],
            "risk_proba": risk_proba,
        }
    )

    return df_result
```

5. Salva il file (`Ctrl + S`).

**Checklist**
- [ ] Esiste `src\ml\predict.py`
- [ ] Le funzioni `load_risk_model`, `prepare_convoy_features`, `predict_convoy_risk_proba` sono presenti

---

### 3. Verifica veloce in REPL (facoltativa ma utile)

1. Nel terminale (con `.venv` attivo), lancia Python:

```bash
python
```

2. Prova i seguenti comandi (assicurati che esista `models\risk_model.pkl` creato in Fase 04):

```python
from src.ml.predict import load_risk_model, predict_convoy_risk_proba

model = load_risk_model("models/risk_model.pkl")
df_result = predict_convoy_risk_proba(model, total_minutes=120, timestep_minutes=10, n_convoys=5)
print(df_result)
```

3. Dovresti vedere una tabella simile a:

```text
   convoy_id  risk_proba
0          1   0.123456
1          2   0.123456
...
```

4. Esci dal REPL:

```python
exit()
```

**Checklist (fine Giorno 1)**

- [ ] `predict.py` è importabile senza errori
- [ ] Posso caricare il modello con `load_risk_model`
- [ ] Posso chiamare `predict_convoy_risk_proba` e ottenere un DataFrame con `risk_proba`

---

## Giorno 2 – Script da console `predict_cli.py`

### Obiettivo del giorno
Creare un **programma da riga di comando** che:

- chiede all’utente i parametri di scenario (come `main_sim.py`),
- carica il modello di rischio,
- stampa la probabilità di rischio per ogni convoglio in modo leggibile.

---

### 1. Creare `src\ml\predict_cli.py`

1. In VS Code, sotto `src\ml`, crea il file `predict_cli.py`.
2. Inserisci il seguente contenuto:

```python
from __future__ import annotations

from .predict import load_risk_model, predict_convoy_risk_proba


def ask_int(prompt: str, default: int) -> int:
    """Chiede un intero all'utente con un valore di default.

    Se l'utente preme solo Invio oppure inserisce un valore non valido,
    viene restituito il valore di default.
    """
    full_prompt = f"{prompt} [{default}]: "

    user_input = input(full_prompt).strip()
    if user_input == "":
        return default

    try:
        value = int(user_input)
    except ValueError:
        print(f"Valore non valido, uso il default: {default}")
        return default

    if value <= 0:
        print(f"Il valore deve essere > 0. Uso il default: {default}")
        return default

    return value


def main() -> None:
    print("=== CLI rischio convoglio – Fase 05 ===")
    print("Questo script usa il modello salvato per stimare il rischio dei convogli.")
    print("Premi Invio per usare i valori di default tra parentesi quadre.")
    print()

    # Valori di default semplici (puoi adattarli)
    default_total_minutes = 120
    default_timestep_minutes = 10
    default_n_convoys = 5

    total_minutes = ask_int("Durata totale simulazione (minuti)", default_total_minutes)
    timestep_minutes = ask_int("Durata di ogni passo (minuti)", default_timestep_minutes)
    n_convoys = ask_int("Numero di convogli da valutare", default_n_convoys)

    print()
    print("Carico il modello di rischio da 'models/risk_model.pkl'...")

    try:
        model = load_risk_model("models/risk_model.pkl")
    except FileNotFoundError as exc:
        print(f"ERRORE: {exc}")
        print("Suggerimento: esegui prima 'python -m src.ml.train_risk_model' per creare il modello.")
        return

    print("Calcolo le probabilità di rischio...")
    df_result = predict_convoy_risk_proba(
        model,
        total_minutes=total_minutes,
        timestep_minutes=timestep_minutes,
        n_convoys=n_convoys,
    )

    print()
    print("=== Risultati ===")
    print("Convoglio  Prob_rischio")
    for _, row in df_result.iterrows():
        convoy_id = int(row["convoy_id"])
        prob = float(row["risk_proba"])
        print(f"{convoy_id:8d}  {prob:11.3f}")

    print()
    print("Interpretazione (semplificata):")
    print("- Prob_rischio ~ 0.0  -> convoglio probabilmente 'sicuro' (secondo il modello).")
    print("- Prob_rischio ~ 1.0  -> convoglio probabilmente 'a rischio' di non completare la missione.")
    print()
    print("Nota: in questa versione tutti i convogli hanno le stesse feature,")
    print("quindi spesso avranno la stessa probabilità. In fasi successive aggiungerai feature più ricche.")


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\ml\predict_cli.py`
- [ ] La funzione `main()` è definita ed esegue la logica di CLI

---

### 2. Eseguire la CLI dal terminale

Nel terminale (con `.venv` attivo), dalla cartella del progetto:

```bash
python -m src.ml.predict_cli
```

Il programma:

- ti chiederà:
  - Durata totale simulazione (minuti)
  - Durata di ogni passo (minuti)
  - Numero di convogli da valutare

- se premi semplicemente **Invio**, usa i default (120, 10, 5)
- poi proverà a caricare `models\risk_model.pkl`

Se il modello **non esiste**, vedrai un messaggio di errore e un suggerimento per eseguire prima `python -m src.ml.train_risk_model` (Fase 04).

Se il modello esiste, dovresti vedere una tabella simile a:

```text
=== Risultati ===
Convoglio  Prob_rischio
       1        0.123
       2        0.123
       3        0.123
       4        0.123
       5        0.123
```

**Checklist (fine Giorno 2)**

- [ ] Posso eseguire `python -m src.ml.predict_cli` senza errori
- [ ] Se il modello manca, vedo un messaggio chiaro su cosa fare
- [ ] Se il modello esiste, vedo una tabella con `Convoglio` e `Prob_rischio`

---

## Giorno 3 – Test automatici per il modulo di prediction

### Obiettivo del giorno
Aggiungere test per il modulo `predict.py` in modo da:

- verificare che `prepare_convoy_features` produca il DataFrame atteso
- verificare che `predict_convoy_risk_proba` funzioni correttamente con un **modello finto** (mock), senza dipendere dal file reale `risk_model.pkl`

> Non testeremo l’interazione **input da tastiera** della CLI (è più complesso), ma ci concentreremo sulla logica di calcolo.

---

### 1. Creare `tests\test_ml_predict.py`

1. In VS Code, vai nella cartella `tests`.
2. Crea il file `test_ml_predict.py`.
3. Inserisci il seguente contenuto:

```python
import numpy as np
import pandas as pd

from src.ml.predict import prepare_convoy_features, predict_convoy_risk_proba


class DummyModel:
    """Modello fittizio per testare la pipeline di prediction.

    Implementa solo predict_proba con una logica semplice e controllabile.
    """

    def predict_proba(self, X):
        # X è un DataFrame o array; ritorniamo sempre:
        # - prob classe 0 = 0.7
        # - prob classe 1 = 0.3
        n_samples = len(X)
        proba = np.tile([0.7, 0.3], (n_samples, 1))
        return proba


def test_prepare_convoy_features_basic():
    df = prepare_convoy_features(total_minutes=120, timestep_minutes=10, n_convoys=3)

    assert list(df.columns) == ["convoy_id", "total_minutes", "timestep_minutes"]
    assert len(df) == 3
    assert df["convoy_id"].tolist() == [1, 2, 3]
    assert df["total_minutes"].tolist() == [120, 120, 120]
    assert df["timestep_minutes"].tolist() == [10, 10, 10]


def test_predict_convoy_risk_proba_with_dummy_model():
    model = DummyModel()
    df_result = predict_convoy_risk_proba(
        model,
        total_minutes=120,
        timestep_minutes=10,
        n_convoys=4,
    )

    # Dovremmo avere 4 righe, una per convoglio
    assert len(df_result) == 4
    assert list(df_result.columns) == ["convoy_id", "risk_proba"]

    # La DummyModel restituisce sempre prob classe 1 = 0.3
    assert np.allclose(df_result["risk_proba"].values, 0.3)
```

4. Salva il file.

**Checklist**
- [ ] Esiste `tests\test_ml_predict.py`
- [ ] Sono definiti i due test `test_prepare_convoy_features_basic` e `test_predict_convoy_risk_proba_with_dummy_model`

---

### 2. Eseguire i test con `pytest`

Nel terminale (con `.venv` attivo), dalla cartella del progetto:

```bash
pytest
```

Controlla che:

- i test precedenti (Fase 01–04) continuino a passare
- i nuovi test in `test_ml_predict.py` passino

Se vedi errori, controlla con attenzione il messaggio e correggi i punti indicati (uso di nomi di file, import, ecc.).

**Checklist (fine Giorno 3)**

- [ ] `pytest` gira senza errori
- [ ] I test in `test_ml_predict.py` passano

---

## Giorno 4 – Esecuzione completa e commit Git Fase 05

### Obiettivo del giorno
- Verificare l’intera catena per la parte di rischio:
  - generazione dataset (Fase 04)
  - training modello (`train_risk_model`)
  - prediction CLI (`predict_cli`)
- Fare un commit Git che contrassegni la Fase 05 come completata.

---

### 1. Pipeline manuale raccomandata

1. (Se non l’hai già fatto di recente) rigenera qualche simulazione:

```bash
python -m src.sim.main_sim
```

2. (Facoltativo) aggiorna il dataset `convoy_risk_dataset.csv` via notebook `build_risk_dataset.ipynb` (Fase 04 Parte 1).  
   - Carica tutti i nuovi CSV
   - Ricostruisci `df_convoys`
   - Salva il CSV in `data\processed`

3. Allena (o riallena) il modello:

```bash
python -m src.ml.train_risk_model
```

4. Lancia i test:

```bash
pytest
```

5. Lancia la CLI di prediction:

```bash
python -m src.ml.predict_cli
```

6. Prova a cambiare i parametri (es: `total_minutes` molto bassi, timestep alti, ecc.) e osserva come varia (o non varia) la probabilità di rischio.

**Checklist**
- [ ] Posso rigenerare il dataset e riallenare il modello senza errori
- [ ] `pytest` passa per tutti i test
- [ ] `python -m src.ml.predict_cli` funziona e mostra le probabilità di rischio

---

### 2. Commit Git della Fase 05

Nel terminale (sempre nella cartella del progetto):

1. Verifica lo stato:

```bash
git status
```

2. Aggiungi i file nuovi/modificati (in particolare `src/ml/predict.py`, `src/ml/predict_cli.py`, `tests/test_ml_predict.py`):

```bash
git add .
```

3. Crea il commit con un messaggio chiaro, ad esempio:

```bash
git commit -m "Fase 05: modulo prediction e CLI rischio convoglio"
```

4. Controlla che il working tree sia pulito:

```bash
git status
```

Dovresti vedere: `nothing to commit, working tree clean`.

**Checklist (fine Giorno 4 – fine Fase 05)**

- [ ] Tutti i test `pytest` passano
- [ ] Posso allenare il modello con `python -m src.ml.train_risk_model`
- [ ] Posso stimare il rischio dei convogli con `python -m src.ml.predict_cli`
- [ ] Ho creato il commit Git “Fase 05: modulo prediction e CLI rischio convoglio”

---

## Fine Fase 05 – Cosa hai ottenuto

Ora hai:

- un **modello di rischio** `models\risk_model.pkl`
- un **modulo di prediction** (`src\ml\predict.py`)
- una **CLI per consultare il modello** (`src\ml\predict_cli.py`)
- test automatici per assicurarti che la parte di prediction continui a funzionare nel tempo

Nelle prossime fasi potrai:
- integrare il modello in una **API web** (es. con FastAPI),
- costruire una **prima interfaccia grafica** (es. con Streamlit) che richiama la CLI o direttamente il modello.

Con questo sei un bel passo più vicino a un MVP effettivamente utilizzabile da te e da altre persone.
