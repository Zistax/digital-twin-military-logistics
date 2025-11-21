# Fase 18 – Model Registry & Champion/Challenger (Parte 1, Giorni 1–3, Windows)

> **Obiettivo pratico (Parte 1)**  
> Introdurre una struttura semplice di **model registry** per il modello di rischio,
> così da poter gestire più versioni (champion, challenger, vecchie versioni):
>
> - cartella `models/registry`,
> - file `registry.json` con le info dei modelli,
> - modulo Python `model_registry.py` per leggere/scrivere il registry,
> - piccolo CLI per vedere quali modelli sono registrati.

> Per ora non cambiamo il modo in cui addestri il modello, ma prepariamo la base.

---

## Struttura Fase 18 – Parte 1

- **Giorno 1** – Cartella `models/registry` + file `registry.json` iniziale
- **Giorno 2** – Modulo `src/ml/model_registry.py` (API base)
- **Giorno 3** – CLI `python -m src.ml.model_registry` + primo record per il modello attuale


---

## Giorno 1 – Cartella `models/registry` + `registry.json`

### Obiettivo del giorno
- Creare la struttura fisica del registry e un file JSON iniziale.

---

### 1. Creare cartella `models/registry`

1. In **Esplora File** o **VS Code**, nella root del progetto, crea la cartella:

   - `models\registry`

Oppure da terminale (PowerShell / cmd), dalla root del progetto:

```bash
mkdir models\registry
```

**Checklist**
- [ ] Esiste la cartella `models\registry`


---

### 2. Creare il file `models\registry\registry.json`

1. In VS Code, dentro `models/registry`, crea il file:

   - `registry.json`

2. Inserisci questo contenuto iniziale:

```json
{
  "models": []
}
```

3. Salva il file.

> Questo file conterrà una lista di modelli registrati.  
> Ogni modello sarà un oggetto con ID, percorso, metriche, flag champion, ecc.

**Checklist**
- [ ] Esiste `models\registry\registry.json` con chiave `models` vuota


---

### 3. (Facoltativo) Aggiungere `models/registry` a `.gitignore`

Puoi decidere se versionare o meno il registry:

- se è un progetto personale e ti fa comodo avere il registry nel repo: **non** aggiungerlo a `.gitignore`;
- se preferisci che resti solo locale (più “prod-like”): aggiungi la cartella a `.gitignore`.

Esempio di riga in `.gitignore`:

```txt
models/registry/
```

Puoi scegliere in base a come usi il repo (per ora puoi anche lasciarlo versionato).

**Checklist (fine Giorno 1)**
- [ ] Struttura `models/registry` pronta
- [ ] `registry.json` inizializzato correttamente


---

## Giorno 2 – Modulo `src/ml/model_registry.py` (API base)

### Obiettivo del giorno
- Creare funzioni Python per:
  - caricare il registry,
  - salvare il registry,
  - registrare un nuovo modello,
  - ottenere il champion.

---

### 1. Creare `src\ml\model_registry.py`

1. In VS Code, dentro `src/ml`, crea il file:

   - `model_registry.py`

2. Inserisci questo codice:

```python
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import json
from datetime import datetime


REGISTRY_PATH = Path("models") / "registry" / "registry.json"


@dataclass
class ModelEntry:
    model_id: str
    model_path: str
    train_dataset_path: str | None = None
    train_timestamp_utc: str | None = None
    metrics: Dict[str, Any] | None = None
    is_champion: bool = False
    notes: str | None = None


def _load_raw_registry(path: Path | None = None) -> Dict[str, Any]:
    registry_path = path or REGISTRY_PATH
    if not registry_path.exists():
        return {"models": []}

    with registry_path.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {"models": []}

    if "models" not in data or not isinstance(data["models"], list):
        data["models"] = []

    return data


def _save_raw_registry(data: Dict[str, Any], path: Path | None = None) -> None:
    registry_path = path or REGISTRY_PATH
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    with registry_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_registry(path: Path | None = None) -> List[ModelEntry]:
    data = _load_raw_registry(path)
    entries: List[ModelEntry] = []

    for item in data.get("models", []):
        entry = ModelEntry(
            model_id=str(item.get("model_id", "")),
            model_path=str(item.get("model_path", "")),
            train_dataset_path=item.get("train_dataset_path"),
            train_timestamp_utc=item.get("train_timestamp_utc"),
            metrics=item.get("metrics"),
            is_champion=bool(item.get("is_champion", False)),
            notes=item.get("notes"),
        )
        entries.append(entry)

    return entries


def save_registry(entries: List[ModelEntry], path: Path | None = None) -> None:
    data = {"models": [asdict(e) for e in entries]}
    _save_raw_registry(data, path)


def register_model(
    model_id: str,
    model_path: Path,
    train_dataset_path: Path | None = None,
    metrics: Dict[str, Any] | None = None,
    is_champion: bool = False,
    notes: str | None = None,
    path: Path | None = None,
) -> ModelEntry:
    """Registra (o aggiorna) un modello nel registry.

    - model_id: ID univoco (es. 'risk_v1', 'risk_20251116T120000Z')
    - model_path: percorso del file .pkl
    - train_dataset_path: CSV usato per il training
    - metrics: dict con metriche (es. {'auc': 0.84, 'brier': 0.17})
    - is_champion: se True, questo modello diventa il champion corrente
    """
    entries = load_registry(path)

    # Se is_champion=True, togliamo il flag agli altri
    if is_champion:
        for e in entries:
            e.is_champion = False

    # Cerchiamo se esiste già un entry con lo stesso ID
    existing = None
    for e in entries:
        if e.model_id == model_id:
            existing = e
            break

    ts_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    if existing is None:
        entry = ModelEntry(
            model_id=model_id,
            model_path=str(model_path),
            train_dataset_path=str(train_dataset_path) if train_dataset_path else None,
            train_timestamp_utc=ts_utc,
            metrics=metrics or {},
            is_champion=is_champion,
            notes=notes,
        )
        entries.append(entry)
    else:
        existing.model_path = str(model_path)
        existing.train_dataset_path = (
            str(train_dataset_path) if train_dataset_path else existing.train_dataset_path
        )
        existing.train_timestamp_utc = existing.train_timestamp_utc or ts_utc
        existing.metrics = metrics or existing.metrics
        existing.is_champion = is_champion
        existing.notes = notes or existing.notes
        entry = existing

    save_registry(entries, path)
    return entry


def get_champion(path: Path | None = None) -> Optional[ModelEntry]:
    """Ritorna il modello marcato come champion, se presente."""
    entries = load_registry(path)
    for e in entries:
        if e.is_champion:
            return e
    return None


def get_model_by_id(model_id: str, path: Path | None = None) -> Optional[ModelEntry]:
    entries = load_registry(path)
    for e in entries:
        if e.model_id == model_id:
            return e
    return None
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\ml\model_registry.py`
- [ ] Ci sono le funzioni `load_registry`, `save_registry`, `register_model`, `get_champion`, `get_model_by_id`


---

### 2. Test veloce dal REPL (senza ancora test automatici)

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python
```

2. Nel prompt Python:

```python
from pathlib import Path
from src.ml.model_registry import load_registry, register_model, get_champion

entries_before = load_registry()
print("Registry iniziale:", entries_before)

register_model(
    model_id="risk_v1",
    model_path=Path("models") / "risk_model.pkl",
    train_dataset_path=Path("data") / "processed" / "convoy_risk_dataset.csv",
    metrics={"auc": 0.80, "brier": 0.18},
    is_champion=True,
    notes="Modello baseline iniziale",
)

entries_after = load_registry()
print("Registry dopo registrazione:", entries_after)

champ = get_champion()
print("Champion:", champ)
```

3. Dovresti vedere che il registry passa da vuoto ad avere un modello `risk_v1`.

4. Esci dal REPL:

```python
exit()
```

**Checklist (fine Giorno 2)**
- [ ] `load_registry()` non esplode con registry vuoto
- [ ] `register_model(...)` aggiunge un record in `registry.json`
- [ ] `get_champion()` restituisce il modello marcato champion


---

## Giorno 3 – CLI `python -m src.ml.model_registry` + primo record “ufficiale”

### Obiettivo del giorno
- Rendere il registry ispezionabile da linea di comando,
- registrare in modo “ufficiale” l’attuale modello di rischio come champion iniziale.

---

### 1. Aggiungere un `main()` in `model_registry.py`

1. Riapri `src/ml/model_registry.py`.
2. In fondo al file, aggiungi:

```python
def main() -> None:
    """Stampa a schermo il contenuto del model registry."""
    entries = load_registry()
    if not entries:
        print("Model registry vuoto (nessun modello registrato).")
        return

    print("=== Model Registry ===")
    for e in entries:
        flag = "[CHAMPION]" if e.is_champion else ""
        print(f"- {e.model_id} {flag}")
        print(f"  path:      {e.model_path}")
        if e.train_dataset_path:
            print(f"  dataset:   {e.train_dataset_path}")
        if e.train_timestamp_utc:
            print(f"  trained:   {e.train_timestamp_utc}")
        if e.metrics:
            print(f"  metrics:   {e.metrics}")
        if e.notes:
            print(f"  notes:     {e.notes}")
        print()


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] `model_registry.py` ha una funzione `main()` eseguibile


---

### 2. Eseguire il CLI del registry

1. Nel terminale, dalla root del progetto:

```bash
python -m src.ml.model_registry
```

2. Se hai già registrato `risk_v1` nel test precedente, dovresti vedere:

```text
=== Model Registry ===
- risk_v1 [CHAMPION]
  path:      models/risk_model.pkl
  dataset:   data/processed/convoy_risk_dataset.csv
  trained:   2025-11-16T10:30:00Z
  metrics:   {'auc': 0.8, 'brier': 0.18}
  notes:     Modello baseline iniziale
```

> I valori saranno diversi (timestamp, metriche), ma la struttura sarà simile.

**Checklist**
- [ ] `python -m src.ml.model_registry` stampa lo stato del registry


---

### 3. (Opzionale) Registrare “ufficialmente” il modello attuale

Se non l’hai fatto nel test, puoi eseguire uno script Python veloce oppure usare il REPL per registrare il modello attuale con metriche più aggiornate (per esempio quelle del report `risk_model.report.json` se lo hai).

> Nella Parte 2 useremo il registry per gestire champion/challenger e comparazioni.

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] Esiste un registry con almeno un modello registrato
- [ ] Sai eseguire `python -m src.ml.model_registry` per vedere i modelli
