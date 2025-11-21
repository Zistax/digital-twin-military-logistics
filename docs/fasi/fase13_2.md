# Fase 13 – Data Contracts & Validatore Ingest (Parte 2, Giorni 4–6, Windows)

> **Scopo Parte 2**  
> Estendere l’idea di **data contract** anche al dataset di rischio / Gold ML e
> collegare la validazione alla pipeline di training, come suggerito in:
>
> - **05 — Strategia Dataset** (Gold ML, anti‑leakage),
> - **08 — Metriche & Validazione** (report JSON per ciclo).

In pratica:
- definisci uno **schema** anche per `convoy_risk_dataset.csv`,
- verifichi che sia coerente prima del training,
- documenti nel README il flusso ingest → validazione → training.


> **Prerequisiti:**
> - Parte 1 completata (`fase13_1.md`),
> - il comando `python -m src.ml.build_risk_dataset` (o equivalente) esiste,
> - `python -m src.ml.train_risk_model` funziona.


---

## Struttura Fase 13 – Parte 2

- **Giorno 4** – JSON Schema per `convoy_risk_dataset.csv` (Gold ML base)
- **Giorno 5** – Validatore per il dataset di rischio + integrazione nel training
- **Giorno 6** – Test, documentazione flusso ingest/validazione e commit Git


---

## Giorno 4 – JSON Schema per il dataset di rischio (Gold)

### Obiettivo del giorno
- Definire uno schema JSON per `data/processed/convoy_risk_dataset.csv`,
- allinearlo (in modo semplice) alle feature che stai usando nel modello.


---

### 1. Analizzare rapidamente le colonne del dataset di rischio

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python
```

Nel REPL Python:

```python
import pandas as pd

df = pd.read_csv("data/processed/convoy_risk_dataset.csv")
print(df.columns.tolist())
print(df.head(3))
```

Segnati l’elenco delle colonne (esempio inventato):

- `total_minutes`
- `timestep_minutes`
- `n_events`
- `max_risk_eff`
- `avg_risk_eff`
- `had_escort`
- `failure`

> Non serve avere **tutte** le feature finali; puoi iniziare con quelle principali
> che usi già nel modello di rischio.


Esci dal REPL:

```python
exit()
```

**Checklist**
- [ ] Conosci l’elenco delle colonne attuali nel dataset di rischio


---

### 2. Creare `data_contracts\ml\convoy_risk_dataset.schema.json`

1. In `data_contracts`, crea una cartella `ml` (se non esiste):

```bash
mkdir data_contracts\ml
```

2. Crea il file:
   - `data_contracts\ml\convoy_risk_dataset.schema.json`

3. Inserisci uno schema di base. Adatta i nomi colonna alla tua realtà.  
   Esempio (da modificare secondo il tuo `df.columns`):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Convoy Risk Dataset",
  "type": "object",
  "properties": {
    "total_minutes": { "type": "number" },
    "timestep_minutes": { "type": "number" },
    "n_events": { "type": "integer" },
    "max_risk_eff": { "type": "number" },
    "avg_risk_eff": { "type": "number" },
    "had_escort": { "type": "boolean" },
    "failure": { "type": "integer" }
  },
  "required": [
    "total_minutes",
    "timestep_minutes",
    "failure"
  ],
  "additionalProperties": true
}
```

4. Salva il file.

> Come per gli eventi, lo schema è **soft**: richiede solo alcune colonne chiave
> e lascia `additionalProperties: true` per non bloccare l’evoluzione delle feature.


**Checklist (fine Giorno 4)**
- [ ] Esiste `data_contracts\ml\convoy_risk_dataset.schema.json`
- [ ] Lo schema riflette (almeno in parte) le colonne reali del dataset


---

## Giorno 5 – Validatore per il dataset di rischio + integrazione training

### Obiettivo del giorno
- Creare un validatore simile a quello degli eventi per `convoy_risk_dataset.csv`,
- richiamarlo all’inizio di `train_risk_model` per fermare il training se il dataset è “rotto”.


---

### 1. Creare `src\data_contracts\ml_validator.py`

1. In `src\data_contracts`, crea il file `ml_validator.py`.
2. Inserisci questo codice (molto simile a `events_validator.py` ma più semplice):

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import csv
import json

from jsonschema import Draft202012Validator


ML_SCHEMA_PATH = Path("data_contracts") / "ml" / "convoy_risk_dataset.schema.json"


class MLValidationResult:
    """Risultato di una validazione CSV ML rispetto a uno schema JSON."""

    def __init__(
        self,
        file_path: Path,
        n_rows: int,
        n_valid: int,
        n_invalid: int,
        errors: List[Dict[str, Any]] | None = None,
    ) -> None:
        self.file_path = file_path
        self.n_rows = n_rows
        self.n_valid = n_valid
        self.n_invalid = n_invalid
        self.errors = errors or []

    @property
    def invalid_ratio(self) -> float:
        if self.n_rows == 0:
            return 0.0
        return self.n_invalid / self.n_rows


def load_ml_schema(schema_path: Path | None = None) -> Dict[str, Any]:
    path = schema_path or ML_SCHEMA_PATH
    if not path.exists():
        raise FileNotFoundError(f"Schema ML non trovato: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_ml_csv(
    csv_path: Path,
    schema: Dict[str, Any] | None = None,
) -> MLValidationResult:
    if schema is None:
        schema = load_ml_schema()

    validator = Draft202012Validator(schema)

    n_rows = 0
    n_valid = 0
    n_invalid = 0
    errors: List[Dict[str, Any]] = []

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            n_rows += 1
            row_obj: Dict[str, Any] = dict(row)
            err_list = list(validator.iter_errors(row_obj))
            if err_list:
                n_invalid += 1
                if len(errors) < 20:
                    errors.append(
                        {
                            "row_number": n_rows,
                            "row": row_obj,
                            "messages": [e.message for e in err_list],
                        }
                    )
            else:
                n_valid += 1

    return MLValidationResult(
        file_path=csv_path,
        n_rows=n_rows,
        n_valid=n_valid,
        n_invalid=n_invalid,
        errors=errors,
    )
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\data_contracts\ml_validator.py`
- [ ] La funzione `validate_ml_csv` restituisce un `MLValidationResult`


---

### 2. Usare il validatore all’inizio di `train_risk_model`

1. Apri `src\ml\train_risk_model.py`.
2. In cima al file, aggiungi l’import:

```python
from src.data_contracts.ml_validator import validate_ml_csv
```

3. Dentro `train_risk_model`, prima di leggere il CSV con pandas, chiama il validatore.

Cerca la parte in cui hai qualcosa tipo:

```python
    df = pd.read_csv(dataset_path)
```

Sostituisci (o precedi) con:

```python
    # Validazione schema dataset ML (data contract)
    from pathlib import Path

    dataset_path = Path(dataset_path)
    ml_validation = validate_ml_csv(dataset_path)
    if ml_validation.n_invalid > 0:
        raise ValueError(
            f"Dataset ML non conforme allo schema: "
            f"{ml_validation.n_invalid}/{ml_validation.n_rows} righe invalide. "
            "Consulta i data contracts in data_contracts/ml."
        )

    df = pd.read_csv(dataset_path)
```

> Se preferisci un approccio meno drastico, potresti solo stampare un warning.
> Ma l’idea “seria” è che un dataset fuori schema **blocchi il training**,
> per evitare di addestrare un modello su dati rotti.

4. Salva il file.

**Checklist**
- [ ] `train_risk_model` importa `validate_ml_csv`
- [ ] All’avvio del training, il dataset viene validato rispetto allo schema ML


---

### 3. Test rapido del validatore ML

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python -m src.ml.train_risk_model
```

2. Se il dataset è conforme allo schema:

   - il training procede come sempre.

3. Se lo schema è troppo restrittivo o hai colonne mancanti:

   - vedrai l’eccezione con il messaggio “Dataset ML non conforme allo schema…”,
   - in tal caso, o adatti lo schema (aggiungi colonne a `properties`), o sistemi il dataset.

**Checklist (fine Giorno 5)**
- [ ] Il training passa con dataset “sano”
- [ ] Il training fallisce in modo chiaro se il dataset non rispetta lo schema ML


---

## Giorno 6 – Test, documentazione flusso ingest/validazione e commit

### Obiettivo del giorno
- Aggiungere almeno un test automatico per il validatore ML,
- descrivere nel README il flusso ingest → validazione → training,
- chiudere la Fase 13 con un commit Git.


---

### 1. Test per `validate_ml_csv`

1. In `tests`, crea (o aggiorna) il file `test_ml_contracts.py`.
2. Inserisci un test base:

```python
from pathlib import Path
import csv

from src.data_contracts.ml_validator import load_ml_schema, validate_ml_csv


def test_validate_ml_csv_basic(tmp_path):
    schema = load_ml_schema()

    csv_path = tmp_path / "convoy_risk_dataset_test.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "total_minutes",
                "timestep_minutes",
                "n_events",
                "max_risk_eff",
                "avg_risk_eff",
                "had_escort",
                "failure",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "total_minutes": "120",
                "timestep_minutes": "10",
                "n_events": "5",
                "max_risk_eff": "1.5",
                "avg_risk_eff": "0.8",
                "had_escort": "True",
                "failure": "0",
            }
        )

    result = validate_ml_csv(csv_path, schema=schema)
    assert result.n_rows == 1
    assert result.n_invalid == 0
```

3. Salva il file.

**Checklist**
- [ ] Esiste `tests\test_ml_contracts.py` con almeno un test base


---

### 2. Aggiornare il README con la sezione “Data Contracts & Validazione”

Apri `README.md` e aggiungi una sezione simile:

```markdown
## Data Contracts & Validazione

Il progetto utilizza **data contracts** (JSON Schema) per i principali file CSV:

- `data_contracts/events/session_events.schema.json` → schema per i log eventi
- `data_contracts/ml/convoy_risk_dataset.schema.json` → schema per il dataset ML di rischio

Per la validazione sono disponibili:

- `python -m src.data_contracts.validate_events` → controlla tutti i `session_*_events.csv`
- la funzione `validate_ml_csv(...)` richiamata all'inizio di `train_risk_model`

In questo modo la pipeline ingest → dataset ML → training fallisce in modo chiaro
se i dati non rispettano lo schema atteso, evitando di addestrare modelli su dati corrotti.
```

Salva il README.

**Checklist**
- [ ] Il README descrive dove sono i data contracts e come funziona la validazione


---

### 3. Eseguire il giro completo di qualità + test

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
run_quality.bat
```

oppure, se preferisci solo i test:

```bash
pytest
```

Assicurati che:

- i test dei data contracts (eventi + ML) passino,
- il training funzioni quando i dati sono sani,
- non ci siano errori nuovi introdotti dalla Fase 13.

**Checklist**
- [ ] `pytest` gira senza errori
- [ ] Eventuali problemi di schema vengono segnalati chiaramente


---

### 4. Commit Git di fine Fase 13

1. Controlla lo stato:

```bash
git status
```

2. Dovresti vedere, tra gli altri:

- `data_contracts/events/session_events.schema.json`
- `data_contracts/ml/convoy_risk_dataset.schema.json`
- `src/data_contracts/events_validator.py`
- `src/data_contracts/validate_events.py`
- `src/data_contracts/ml_validator.py`
- `tests/test_events_contracts.py`
- `tests/test_ml_contracts.py`
- `README.md`

3. Aggiungi i file:

```bash
git add .
```

4. Crea il commit:

```bash
git commit -m "Fase 13: data contracts ed ingest validator per eventi e dataset ML"
```

5. Verifica che il working tree sia pulito:

```bash
git status
```

Dovresti vedere `nothing to commit, working tree clean`.

**Checklist (fine Giorno 6 – fine Fase 13)**
- [ ] Esistono data contracts per eventi e dataset ML
- [ ] Esistono validator Python per entrambi
- [ ] Il training del modello verifica lo schema ML prima di partire
- [ ] Il README spiega il flusso ingest → validazione → training
- [ ] Ho creato il commit Git di fine Fase 13


---

## Fine Fase 13 – Cosa hai ottenuto

Con la Fase 13 hai portato nel tuo progetto concetti “seri” di **data engineering**:

- **data contracts** JSON Schema per log e dataset ML,
- validatori ingest in Python con test automatici,
- integrazione della validazione nel training del modello,
- documentazione chiara nel README.

Questi passi ti proteggono da CSV rotti, colonne mancanti o cambiamenti silenziosi nei dati, e
preparano il terreno per fasi ancora più avanzate (pipeline Silver/Gold più ricche,
drift detection, RL, ecc.).