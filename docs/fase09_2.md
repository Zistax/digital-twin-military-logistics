# Fase 09 – Config & riproducibilità base (Parte 2, Giorni 4–6, Windows)

> **Scopo Parte 2**  
> Portare la configurazione YAML anche nella parte **ML** e migliorare la **riproducibilità** del training:
>
> - usare `conf\ml\default.yml` in `train_risk_model`,
> - centralizzare l’uso di `random_state`,
> - salvare un piccolo **report JSON** accanto al modello,
> - aggiungere test minimi sulla config ML.

> **Prerequisito**: hai completato la Parte 1 (`fase09_1.md`) e:
> - `load_ml_config()` funziona,
> - la simulazione usa già `load_sim_config()` per i default.


---

## Struttura Fase 09 – Parte 2

- **Giorno 4** – Integrare `load_ml_config()` in `train_risk_model`
- **Giorno 5** – Salvare un report JSON di training e aggiungere test
- **Giorno 6** – Verifiche finali di riproducibilità e commit Git


---

## Giorno 4 – Usare `conf\ml\default.yml` in `train_risk_model`

### Obiettivo del giorno
- Modificare `src\ml\train_risk_model.py` per leggere i parametri ML dal file YAML,
- assicurarti che `random_state` sia usato in modo coerente (split + modello).


---

### 1. Aggiungere l’import di `load_ml_config`

Apri `src\ml\train_risk_model.py` in VS Code.

In cima al file, dove ci sono gli import, aggiungi:

```python
from src.config.config_loader import load_ml_config
```

Assicurati di non duplicare import già esistenti.

**Checklist**
- [ ] `train_risk_model.py` importa `load_ml_config`


---

### 2. Usare la config ML dentro `train_risk_model`

Cerca la funzione `train_risk_model` in `src\ml\train_risk_model.py`.  
Dovrebbe avere una forma simile a quella definita in Fase 04 (può avere piccole differenze).

All’inizio della funzione, **subito dopo** l’eventuale stampa iniziale, aggiungi qualcosa come:

```python
    # Carichiamo la configurazione ML (test_size, random_state, ecc.)
    ml_conf = load_ml_config()

    test_size = float(ml_conf.get("test_size", 0.3))
    random_state = int(ml_conf.get("random_state", 42))
    max_iter = int(ml_conf.get("max_iter", 1000))
```

Poi, quando chiami `split_features_labels`, passa `test_size` e `random_state` presi dalla config.

Ad esempio, se prima avevi:

```python
    X_train, X_test, y_train, y_test = split_features_labels(df)
```

sostituiscilo con:

```python
    X_train, X_test, y_train, y_test = split_features_labels(
        df,
        test_size=test_size,
        random_state=random_state,
    )
```

Infine, quando crei il modello `LogisticRegression`, passa anche `random_state` e `max_iter`:

Se prima avevi, ad esempio:

```python
    model = LogisticRegression(max_iter=1000)
```

sostituisci con:

```python
    model = LogisticRegression(max_iter=max_iter, random_state=random_state)
```

> **Idea**: così, se cambi `random_state` in `conf\ml\default.yml`, puoi ripetere l’esperimento con un seed diverso in modo controllato.

Salva il file.

**Checklist**
- [ ] `train_risk_model` legge `test_size`, `random_state`, `max_iter` da `ml_conf`
- [ ] `split_features_labels` usa `test_size` e `random_state` della config
- [ ] `LogisticRegression` usa `max_iter` e `random_state` della config


---

### 3. Eseguire il training con la nuova config

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python -m src.ml.train_risk_model
```

Dovrebbe:

- caricare il dataset,
- dividere in train/test,
- addestrare il modello con i parametri presi da `conf\ml\default.yml`,
- salvare `models\risk_model.pkl` come prima.

**Checklist (fine Giorno 4)**
- [ ] `python -m src.ml.train_risk_model` funziona dopo le modifiche
- [ ] Modificando `conf\ml\default.yml` (es. `test_size` o `max_iter`) il training si adatta


---

## Giorno 5 – Salvare un report JSON e aggiungere test

### Obiettivo del giorno
- Salvare un **report JSON** con le metriche di training accanto al modello,
- aggiungere un test semplice che controlli l’esistenza del report.


---

### 1. Salvare il report JSON accanto a `risk_model.pkl`

In `src\ml\train_risk_model.py`, nella funzione `train_risk_model`, dopo aver calcolato `y_pred` e stampato le metriche, aggiungi la logica per creare un piccolo report.

Cerca il punto dove calcoli e stampi le metriche, ad esempio:

```python
    print("=== Confusion Matrix ===")
    print(confusion_matrix(y_test, y_pred))

    print()
    print("=== Classification Report ===")
    print(classification_report(y_test, y_pred, digits=3))
```

Sotto queste righe, aggiungi:

```python
    # Prepariamo un report in forma strutturata (dict) per salvarlo su disco
    report_dict = {
        "params": {
            "test_size": test_size,
            "random_state": random_state,
            "max_iter": max_iter,
        },
        "metrics": {
            "classification_report": classification_report(
                y_test, y_pred, digits=3, output_dict=True
            ),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        },
    }
```

> Nota: `output_dict=True` fa sì che `classification_report` restituisca un dizionario invece di una stringa.

Poi, subito dopo il salvataggio del modello (`joblib.dump(model, model_path)`), aggiungi:

```python
    # Salviamo il report come JSON accanto al modello
    import json

    report_path = model_path.with_suffix(".report.json")
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)

    print(f"Report di training salvato in: {report_path}")
```

Salva il file.

**Checklist**
- [ ] `train_risk_model` costruisce un dict `report_dict` con parametri + metriche
- [ ] Il report viene salvato come `models\risk_model.report.json`


---

### 2. Eseguire il training e verificare il file di report

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python -m src.ml.train_risk_model
```

Poi controlla, con Esplora File o terminale, che nella cartella `models` siano presenti:

- `risk_model.pkl`
- `risk_model.report.json`

Puoi aprire `risk_model.report.json` con VS Code per vedere il contenuto (è un JSON abbastanza leggibile).

**Checklist**
- [ ] Dopo il training, vedo `risk_model.report.json` accanto a `risk_model.pkl`
- [ ] Il JSON contiene sia i parametri di training sia le metriche


---

### 3. Aggiungere un test semplice per il report di training

1. In VS Code, nella cartella `tests`, crea un file chiamato ad esempio `test_train_report.py`.
2. Inserisci un contenuto simile (adatta se necessario al tuo codice):

```python
from pathlib import Path

import pandas as pd

from src.ml.train_risk_model import train_risk_model


def test_train_risk_model_creates_report(tmp_path):
    """Verifica che il training crei sia il modello che il report JSON."""
    # Creiamo un piccolo dataset finto
    data = {
        "total_minutes": [30, 60, 120, 120],
        "timestep_minutes": [10, 10, 10, 20],
        "risk_label": [1, 0, 0, 1],
    }
    df = pd.DataFrame(data)

    dataset_path = tmp_path / "dataset.csv"
    df.to_csv(dataset_path, index=False)

    model_path = tmp_path / "risk_model_test.pkl"

    # Eseguiamo il training passando percorsi personalizzati
    train_risk_model(dataset_path=dataset_path, model_path=model_path)

    # Controlliamo che il modello e il report esistano
    assert model_path.exists()

    report_path = model_path.with_suffix(".report.json")
    assert report_path.exists()
```

> Nota: questo test presuppone che `train_risk_model` accetti i parametri `dataset_path` e `model_path` come nell’implementazione delle fasi precedenti. Se hai nomi leggermente diversi, adatta di conseguenza.

3. Salva il file.

**Checklist (fine Giorno 5)**
- [ ] Il training crea il file `risk_model.report.json` accanto al modello
- [ ] Esiste un test `test_train_report.py` che controlla che il report venga creato


---

## Giorno 6 – Verifiche di riproducibilità e commit Git

### Obiettivo del giorno
- Eseguire tutti i test,
- fare un piccolo esperimento di riproducibilità cambiando `random_state`,
- creare un commit Git per chiudere la Fase 09.


---

### 1. Eseguire tutti i test con `pytest`

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest
```

Assicurati che:

- passino i test delle fasi precedenti,
- passi anche `test_train_report.py`,
- non ci siano errori relativi a `load_ml_config` o all’uso di `random_state`.

**Checklist**
- [ ] `pytest` gira senza errori


---

### 2. Esperimento rapido di riproducibilità con `random_state`

1. Apri `conf\ml\default.yml`.
2. Segnati da qualche parte (anche a mano) il valore attuale di `random_state` (es. 42).
3. Esegui il training **due volte** con lo stesso `random_state`:

```bash
python -m src.ml.train_risk_model
python -m src.ml.train_risk_model
```

4. Confronta (anche solo “a occhio”) i contenuti di `risk_model.report.json` dopo ogni run:
   - dovrebbero essere identici (salvo il fatto che eventualmente venga sovrascritto lo stesso file).
5. Poi modifica `random_state` in `conf\ml\default.yml` (es. 123) e riesegui:

```bash
python -m src.ml.train_risk_model
```

6. Ora `risk_model.report.json` potrebbe avere valori leggermente diversi (dipende dal dataset), a indicare che hai cambiato seed e quindi “esperimento”.

> Non stiamo facendo un confronto automatico, ma solo un esercizio mentale:  
> **stessa config → stesso seed → stessi risultati**,  
> **config diversa → seed diverso → risultati potenzialmente diversi**.

**Checklist**
- [ ] Ho capito il ruolo di `random_state` per la riproducibilità
- [ ] Con lo stesso `random_state` ottengo sempre lo stesso training (sovrascrivendo il report)
- [ ] Cambiando `random_state` posso esplorare esperimenti diversi in modo controllato


---

### 3. (Facoltativo) Nota nel README sulla config & riproducibilità

Apri `README.md` e aggiungi una breve sezione, ad esempio:

```markdown
## Configurazione & riproducibilità

Il progetto utilizza file YAML nella cartella `conf/` per gestire i valori di default:

- `conf/sim/default.yml` → parametri di simulazione (durata, timestep, n_convoys, ecc.)
- `conf/ml/default.yml` → parametri di training ML (test_size, random_state, max_iter, ecc.)

Le funzioni `load_sim_config()` e `load_ml_config()` (in `src/config/config_loader.py`)
caricano queste impostazioni. In particolare:

- il campo `random_state` in `conf/ml/default.yml` controlla la riproducibilità
  del train/test split e del modello di rischio.

Ad ogni esecuzione di `python -m src.ml.train_risk_model` viene creato/aggiornato
un file `models/risk_model.report.json` con un riepilogo dei parametri di training
e delle metriche ottenute.
```

Salva il `README.md`.

**Checklist**
- [ ] Il `README.md` menziona l’uso dei file `conf/` e il ruolo di `random_state`


---

### 4. Commit Git di fine Fase 09

Nel terminale, dalla root del progetto:

```bash
git status
```

Dovresti vedere i file nuovi/modificati, tra cui:

- `conf/sim/default.yml` (e/o altri in `conf/`)
- `conf/ml/default.yml`
- `src/config/config_loader.py`
- `src/ml/train_risk_model.py`
- `tests/test_train_report.py`
- eventualmente `README.md`

1. Aggiungi i file:

```bash
git add .
```

2. Crea il commit con un messaggio chiaro, ad esempio:

```bash
git commit -m "Fase 09: config YAML e riproducibilità base per simulazione e modello"
```

3. Verifica che il working tree sia pulito:

```bash
git status
```

Dovresti vedere: `nothing to commit, working tree clean`.

**Checklist (fine Giorno 6 – fine Fase 09)**
- [ ] Le config YAML (`conf/`) sono in uso per simulazione e ML
- [ ] `train_risk_model` legge i parametri da `conf/ml/default.yml`
- [ ] Viene creato un report JSON di training accanto al modello
- [ ] I test (`pytest`) passano
- [ ] Ho creato il commit Git di fine Fase 09


---

## Fine Fase 09 – Cosa hai ottenuto

Con la Fase 09 completata, il tuo progetto è più **ordinato e riproducibile**:

- I valori di default di simulazione e ML sono **configurabili** tramite file YAML.
- Puoi cambiare parametri (durata, test_size, random_state, max_iter, ...) **senza toccare il codice**.
- Il training del modello genera un **report JSON** con parametri e metriche,
  utile per ricordare come è stato ottenuto un certo modello.
- Hai iniziato a ragionare in termini di **esperimenti ripetibili** (stessa config → stessi risultati).

Nelle fasi successive potrai:
- raffinare ulteriormente il sistema di config (es. ambienti `dev`, `prod`),
- aggiungere altri parametri (es. tipo di modello, feature da usare),
- collegare queste config al resto della pipeline (API, UI, ecc.).
