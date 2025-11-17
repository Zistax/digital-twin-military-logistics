# Fase 13 – Data Contracts & Validatore Ingest (Parte 1, Giorni 1–3, Windows)

> **Scopo Fase 13 (visione generale)**  
> Cominciare a mettere in pratica quanto descritto in **“04 — Logging & Schema Dati”** e **“05 — Strategia Dataset”**:
>
> - avere **data contracts espliciti** (JSON Schema) per i file principali,
> - validare i CSV prodotti dal simulatore,
> - mandare eventuali righe invalide in **quarantena** invece di romperti le pipeline.

In **Parte 1** ti concentri sugli **event log** (`session_*_events.csv`).  
In **Parte 2** (file `fase13_2.md`) estenderai il concetto al dataset di rischio / Gold ML.

> **Prerequisiti:**
> - Fase 03–04: il simulatore genera già file `session_{id}_events.csv` in `data\raw`,
> - Fase 05–08: pipeline rischio base funzionante,
> - Fase 11: `pytest` e `run_quality.bat` funzionano.


---

## Struttura Fase 13 – Parte 1

- **Giorno 1** – Creare cartella `data_contracts/` e JSON Schema per gli eventi
- **Giorno 2** – Implementare un validatore Python per gli event log
- **Giorno 3** – Integrare il validatore nel flusso ed aggiungere test


---

## Giorno 1 – Cartella `data_contracts/` + JSON Schema eventi

### Obiettivo del giorno
- Creare la cartella `data_contracts/`,
- definire un JSON Schema minimo per `session_*_events.csv`,
- allinearlo (a grandi linee) a quanto descritto in `04 — Logging & Schema Dati`.


---

### 1. Creare cartella `data_contracts`

1. In **VS Code**, nella root del progetto:
   - clic destro → **New Folder** → `data_contracts`
2. All’interno di `data_contracts`, crea eventualmente una sotto-cartella per gli eventi:

   - `data_contracts/events` (facoltativo, ma pulito)

Oppure da terminale:

```bash
mkdir data_contracts
mkdir data_contracts\events
```

**Checklist**
- [ ] Esiste la cartella `data_contracts`
- [ ] (Opzionale) Esiste `data_contracts\events`


---

### 2. Creare `data_contracts\events\session_events.schema.json`

1. In VS Code, crea il file:
   - `data_contracts\events\session_events.schema.json`
2. Inserisci un primo schema **minimo**, ispirato a `04 — Logging & Schema Dati`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Session Events",
  "type": "object",
  "properties": {
    "ts_utc": { "type": "string" },
    "t_step": { "type": "integer" },
    "event": { "type": "string" },
    "session_id": { "type": "string" },
    "convoy_id": { "type": "integer" },
    "priority": { "type": "string" },
    "risk_eff": { "type": "number" },
    "qty": { "type": "number" },
    "depot_id": { "type": "string" },
    "depot_stock": { "type": "number" },
    "phase": { "type": "string" },
    "schema_version": { "type": "string" }
  },
  "required": [
    "ts_utc",
    "t_step",
    "event",
    "session_id",
    "convoy_id",
    "schema_version"
  ],
  "additionalProperties": true
}
```

> Questo è volutamente **minimo** e permissivo (`additionalProperties: true`).  
> Ti serve come “rete di sicurezza”: almeno i campi chiave devono esserci e avere il tipo giusto.

3. Salva il file.

**Checklist**
- [ ] Esiste `data_contracts\events\session_events.schema.json`
- [ ] Lo schema contiene almeno i campi chiave (`ts_utc`, `t_step`, `event`, `session_id`, `convoy_id`, `schema_version`)


---

### 3. (Opzionale) Aggiungere enum per `event`, `phase`, `priority`

Se vuoi essere un po’ più rigido, puoi aggiungere enumerazioni come da documento `04 — Logging & Schema Dati`:

- priority: `low|medium|high`
- eventi (estratto): `load|unload|attack|breakdown|repaired|mission_complete|hold|...`
- fasi: `idle|load|travel|unload|hold|reroute|regroup|complete|parked`

Esempio (solo per priority):

```json
"priority": {
  "type": "string",
  "enum": ["low", "medium", "high"]
}
```

Puoi farlo più avanti, per ora lo schema “soft” va più che bene.

**Checklist (fine Giorno 1)**
- [ ] La struttura `data_contracts/` è pronta
- [ ] Esiste uno schema JSON per gli event log, anche se minimale


---

## Giorno 2 – Validatore Python per gli event log

### Obiettivo del giorno
- Aggiungere la dipendenza `jsonschema`,
- creare un modulo Python `src\data_contracts\events_validator.py`,
- implementare una funzione che valida un singolo file `session_*_events.csv`.

---

### 1. Aggiungere `jsonschema` a `requirements.txt`

1. Apri `requirements.txt`.
2. Aggiungi (se non c’è già):

```txt
jsonschema
```

3. Salva il file.

4. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pip install -r requirements.txt
```

**Checklist**
- [ ] `requirements.txt` contiene `jsonschema`
- [ ] `pip install -r requirements.txt` completato senza errori gravi


---

### 2. Creare package `src\data_contracts`

1. In VS Code, nella cartella `src`, crea una nuova cartella `data_contracts`.
2. Dentro `src\data_contracts`, crea il file vuoto `__init__.py`.

Oppure da terminale:

```bash
mkdir src\data_contracts
type NUL > src\data_contracts\__init__.py
```

**Checklist**
- [ ] Esiste `src\data_contracts`
- [ ] Esiste `src\data_contracts\__init__.py`


---

### 3. Creare `src\data_contracts\events_validator.py`

1. In `src\data_contracts`, crea il file `events_validator.py`.
2. Inserisci questo codice:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import csv
import json

from jsonschema import Draft202012Validator


SCHEMA_PATH = Path("data_contracts") / "events" / "session_events.schema.json"


class ValidationResult:
    """Risultato di una validazione CSV rispetto a uno schema JSON."""

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

    def __repr__(self) -> str:  # pragma: no cover - solo per debug
        return (
            f"ValidationResult(file_path={self.file_path}, "
            f"n_rows={self.n_rows}, n_valid={self.n_valid}, n_invalid={self.n_invalid})"
        )


def load_events_schema(schema_path: Path | None = None) -> Dict[str, Any]:
    """Carica lo schema JSON per gli eventi."""
    path = schema_path or SCHEMA_PATH
    if not path.exists():
        raise FileNotFoundError(f"Schema eventi non trovato: {path}")

    with path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    return schema


def validate_events_file(csv_path: Path, schema: Dict[str, Any] | None = None) -> ValidationResult:
    """Valida un file session_*_events.csv rispetto allo schema JSON.

    - csv_path: percorso del file CSV da validare.
    - schema: schema JSON già caricato (opzionale).

    Restituisce un ValidationResult con conteggio righe valide/invalid
    e una lista (limitata) di errori.
    """
    if schema is None:
        schema = load_events_schema()

    validator = Draft202012Validator(schema)

    n_rows = 0
    n_valid = 0
    n_invalid = 0
    errors: List[Dict[str, Any]] = []

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            n_rows += 1
            # jsonschema si aspetta un dict; i valori sono stringhe, ma lo schema e' soft.
            row_obj: Dict[str, Any] = dict(row)
            err_list = list(validator.iter_errors(row_obj))
            if err_list:
                n_invalid += 1
                # Salviamo solo i primi N errori per non esplodere
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

    return ValidationResult(
        file_path=csv_path,
        n_rows=n_rows,
        n_valid=n_valid,
        n_invalid=n_invalid,
        errors=errors,
    )
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\data_contracts\events_validator.py`
- [ ] La funzione `validate_events_file` restituisce un `ValidationResult`


---

### 4. Script CLI `python -m src.data_contracts.validate_events`

Per comodità, creiamo un piccolo modulo eseguibile da linea di comando.

1. In `src\data_contracts`, crea il file `validate_events.py`.
2. Inserisci:

```python
from __future__ import annotations

from pathlib import Path

from .events_validator import validate_events_file


def main() -> None:
    raw_dir = Path("data") / "raw"
    if not raw_dir.exists():
        print("Cartella data/raw non trovata. Nessun file da validare.")
        return

    csv_files = sorted(raw_dir.glob("session_*_events.csv"))
    if not csv_files:
        print("Nessun file session_*_events.csv trovato in data/raw.")
        return

    print(f"Trovati {len(csv_files)} file di eventi da validare.\n")

    for csv_path in csv_files:
        print(f"Validazione {csv_path} ...")
        result = validate_events_file(csv_path)
        print(
            f"  Righe: {result.n_rows}, valide: {result.n_valid}, "
            f"invalid: {result.n_invalid} (ratio={result.invalid_ratio:.3f})"
        )
        if result.errors:
            print("  Esempi di errori:")
            for err in result.errors[:3]:
                print(f"    - row {err['row_number']}: {err['messages']}")

        print()

    print("Validazione eventi completata.")


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\data_contracts\validate_events.py` con una funzione `main()`
- [ ] Il modulo usa `validate_events_file` per tutti i `session_*_events.csv`


---

### 5. Prova rapida da linea di comando

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python -m src.data_contracts.validate_events
```

2. Se hai già generato dei file `session_*_events.csv` con il simulatore, dovresti vedere un output simile:

```text
Trovati 2 file di eventi da validare.

Validazione data/raw/session_001_events.csv ...
  Righe: 240, valide: 240, invalid: 0 (ratio=0.000)

Validazione data/raw/session_002_events.csv ...
  Righe: 260, valide: 259, invalid: 1 (ratio=0.004)
  Esempi di errori:
    - row 17: ["'schema_version' is a required property"]

Validazione eventi completata.
```

**Checklist (fine Giorno 2)**
- [ ] `jsonschema` è installato
- [ ] Il comando `python -m src.data_contracts.validate_events` funziona
- [ ] Vedi un report basic di validazione per ogni `session_*_events.csv`


---

## Giorno 3 – Quarantena righe invalide + test automatici

### Obiettivo del giorno
- Aggiungere una **quarantena** per le righe invalide (come da doc: “righe invalide in quarantena; hard-fail se >0.5%”),
- aggiungere un **test pytest** che controlli che la validazione funzioni.


---

### 1. Aggiungere quarantena in `events_validator.py`

Vogliamo che, opzionalmente, la funzione `validate_events_file` possa:

- salvare le righe invalide in un file tipo `data/quarantine/{nome_file}_invalid.csv`,
- se il rapporto invalid/total supera una soglia (es. 0.5%), segnalare un problema “grave”.

1. Riapri `src\data_contracts\events_validator.py`.
2. Modifica la firma di `validate_events_file` per aggiungere due parametri opzionali:

```python
def validate_events_file(
    csv_path: Path,
    schema: Dict[str, Any] | None = None,
    quarantine_dir: Path | None = None,
    invalid_ratio_hard_fail: float | None = None,
) -> ValidationResult:
```

3. Dopo il ciclo di lettura, prima del `return`, aggiungi la logica di quarantena:

```python
    # Scriviamo eventualmente le righe invalide in quarantena
    if quarantine_dir is not None and n_invalid > 0 and errors:
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        q_path = quarantine_dir / f"{csv_path.stem}_invalid.csv"

        # Usiamo i row salvati in errors (massimo 20) per non esplodere.
        # Se vuoi tutte le righe invalide, servirebbe salvarle durante il loop.
        import csv as _csv

        with q_path.open("w", encoding="utf-8", newline="") as f_q:
            fieldnames = sorted(errors[0]["row"].keys())
            writer = _csv.DictWriter(f_q, fieldnames=fieldnames)
            writer.writeheader()
            for err in errors:
                writer.writerow(err["row"])
```

4. Subito dopo, se `invalid_ratio_hard_fail` è impostato, puoi lanciare un’eccezione se la quota è troppo alta:

```python
    if invalid_ratio_hard_fail is not None and n_rows > 0:
        ratio = n_invalid / n_rows
        if ratio > invalid_ratio_hard_fail:
            raise ValueError(
                f"Troppi record invalidi in {csv_path}: "
                f"{n_invalid}/{n_rows} (ratio={ratio:.3f}) "
                f"> soglia {invalid_ratio_hard_fail:.3f}"
            )
```

5. Il `return ValidationResult(...)` resta uguale.

6. Salva il file.

**Checklist**
- [ ] `validate_events_file` accetta `quarantine_dir` e `invalid_ratio_hard_fail`
- [ ] In caso di righe invalide, vengono scritte in un CSV in `quarantine_dir`


---

### 2. Usare la quarantena nel CLI `validate_events.py`

Nel file `src\data_contracts\validate_events.py`, modifica la chiamata a `validate_events_file`:

1. In cima al file, aggiungi:

```python
QUARANTINE_DIR = Path("data") / "quarantine"
```

2. Nella funzione `main()`, sostituisci:

```python
        result = validate_events_file(csv_path)
```

con:

```python
        result = validate_events_file(
            csv_path,
            quarantine_dir=QUARANTINE_DIR,
            invalid_ratio_hard_fail=None,  # puoi impostare una soglia se vuoi
        )
```

3. Salva il file.

**Checklist**
- [ ] Il CLI ora passa `quarantine_dir` a `validate_events_file`
- [ ] I file di quarantena vengono salvati sotto `data\quarantine` se ci sono righe invalide


---

### 3. Aggiungere un test pytest per la validazione eventi

1. In `tests`, crea il file `test_events_contracts.py`.
2. Inserisci un test semplice che costruisca un CSV temporaneo e lo validi:

```python
from pathlib import Path
import csv

from src.data_contracts.events_validator import (
    load_events_schema,
    validate_events_file,
)


def test_validate_events_file_basic(tmp_path):
    # Prepariamo uno schema finto minimo (potresti usare direttamente quello reale)
    schema = load_events_schema()

    # Creiamo un piccolo CSV valido
    csv_path = tmp_path / "session_123_events.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ts_utc",
                "t_step",
                "event",
                "session_id",
                "convoy_id",
                "schema_version",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "ts_utc": "2025-01-01T00:00:00Z",
                "t_step": "0",
                "event": "load",
                "session_id": "sess_001",
                "convoy_id": "1",
                "schema_version": "1.0",
            }
        )

    result = validate_events_file(csv_path, schema=schema)
    assert result.n_rows == 1
    assert result.n_invalid == 0
```

3. Salva il file.

**Checklist**
- [ ] Esiste `tests\test_events_contracts.py`
- [ ] Il test crea un CSV minimale e lo valida senza errori


---

### 4. Lanciare `pytest` (o `run_quality.bat`)

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest tests/test_events_contracts.py
```

oppure:

```bash
run_quality.bat
```

Se tutto è a posto, dovresti vedere il test verde.

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] `data_contracts/` contiene almeno lo schema per gli event log
- [ ] Esiste un validatore Python per `session_*_events.csv`
- [ ] Il CLI `python -m src.data_contracts.validate_events` funziona
- [ ] Esiste almeno un test automatico per la validazione


---

Con questa Parte 1 hai introdotto i **data contracts** sugli eventi e un
primo **validatore ingest** che evita che CSV “rotti” entrino silenziosamente
nella pipeline.  

Nella **Parte 2** (`fase13_2.md`) farai:
- data contract per il dataset di rischio / Gold,
- integrazione del validatore nel training del modello,
- documentazione del flusso ingest → validazione → training.