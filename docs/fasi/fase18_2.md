# Fase 18 – Model Registry & Champion/Challenger (Parte 2, Giorni 4–6, Windows)

> **Obiettivo pratico (Parte 2)**  
> Utilizzare il model registry per impostare un flusso **champion/challenger**:
>
> - confrontare un modello champion con uno o più challenger,
> - generare un piccolo report di comparazione,
> - aggiungere test base per il registry e la logica di promozione,
> - documentare il tutto nel `README.md`.


---

## Struttura Fase 18 – Parte 2

- **Giorno 4** – Modulo `champion_challenger.py` (logica di confronto)
- **Giorno 5** – Test su `model_registry` e su `decide_promotion`
- **Giorno 6** – Documentare “Model registry & champion/challenger” e commit finale


---

## Giorno 4 – Modulo `champion_challenger.py` (confronto metriche)

### Obiettivo del giorno
- Creare un modulo che:
  - usa il registry per trovare champion + challenger,
  - valuta i modelli con `evaluate_model_on_dataset` (già creato in Fase 17),
  - decide se promuovere il challenger a nuovo champion,
  - salva un report JSON della comparazione.


---

### 1. Creare `src\ml\champion_challenger.py`

1. In VS Code, dentro `src/ml`, crea il file:

   - `champion_challenger.py`

2. Inserisci questo codice:

```python
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import json
from datetime import datetime

from src.ml.model_registry import (
    REGISTRY_PATH,
    ModelEntry,
    load_registry,
    register_model,
    get_champion,
    get_model_by_id,
)
from src.ml.drift_monitor import evaluate_model_on_dataset


BASE_DIR = Path(".")
DEFAULT_DATASET_PATH = BASE_DIR / "data" / "processed" / "convoy_risk_dataset.csv"
REPORTS_DIR = BASE_DIR / "data" / "monitoring" / "reports"


@dataclass
class ModelMetrics:
    model_id: str
    metrics: Dict[str, Any]


@dataclass
class PromotionDecision:
    champion_id: str | None
    challenger_id: str
    promote: bool
    reasons: List[str]
    metrics_champion: Dict[str, Any] | None
    metrics_challenger: Dict[str, Any]


def decide_promotion(
    metrics_champion: Dict[str, Any] | None,
    metrics_challenger: Dict[str, Any],
    min_auc_improvement: float = 0.01,
    max_brier_increase: float = 0.0,
) -> PromotionDecision:
    """Decide se promuovere un challenger a nuovo champion.

    Regole base:
    - se non esiste champion -> promuovi sempre il challenger
    - se esiste:
      - richiedi AUC_challenger >= AUC_champion + min_auc_improvement
      - richiedi Brier_challenger <= Brier_champion + max_brier_increase
    """
    reasons: List[str] = []

    if metrics_champion is None:
        reasons.append("Nessun champion registrato: il challenger diventerebbe il primo champion.")
        return PromotionDecision(
            champion_id=None,
            challenger_id="",
            promote=True,
            reasons=reasons,
            metrics_champion=None,
            metrics_challenger=metrics_challenger,
        )

    auc_c = float(metrics_champion.get("auc", 0.0))
    brier_c = float(metrics_champion.get("brier", 1.0))

    auc_chall = float(metrics_challenger.get("auc", 0.0))
    brier_chall = float(metrics_challenger.get("brier", 1.0))

    promote = True

    if auc_chall < auc_c + min_auc_improvement:
        promote = False
        reasons.append(
            f"AUC challenger {auc_chall:.3f} non migliora abbastanza rispetto al champion "
            f"{auc_c:.3f} (min delta {min_auc_improvement:.3f})."
        )

    if brier_chall > brier_c + max_brier_increase:
        promote = False
        reasons.append(
            f"Brier challenger {brier_chall:.3f} peggiore del champion {brier_c:.3f} "
            f"(max aumento {max_brier_increase:.3f})."
        )

    if promote and not reasons:
        reasons.append("Challenger migliora AUC e non peggiora Brier oltre la soglia.")

    return PromotionDecision(
        champion_id="",
        challenger_id="",
        promote=promote,
        reasons=reasons,
        metrics_champion=metrics_champion,
        metrics_challenger=metrics_challenger,
    )


def run_champion_challenger(
    challenger_id: str,
    dataset_path: Path | None = None,
) -> Dict[str, Any]:
    """Esegue il confronto champion/challenger su un dataset dato.

    - challenger_id: ID del modello challenger nel registry
    - dataset_path: percorso del dataset; se None usa il dataset Gold default
    """
    ds_path = dataset_path or DEFAULT_DATASET_PATH

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Carichiamo champion e challenger dal registry
    champion_entry = get_champion()
    challenger_entry = get_model_by_id(challenger_id)

    if challenger_entry is None:
        raise ValueError(f"Challenger con ID '{challenger_id}' non trovato nel registry.")

    metrics_champion: Dict[str, Any] | None = None
    champion_id: Optional[str] = None

    if champion_entry is not None:
        champion_id = champion_entry.model_id
        metrics_champion = evaluate_model_on_dataset(
            model_path=Path(champion_entry.model_path),
            dataset_path=ds_path,
            label_col="failure",
        )

    metrics_challenger = evaluate_model_on_dataset(
        model_path=Path(challenger_entry.model_path),
        dataset_path=ds_path,
        label_col="failure",
    )

    decision = decide_promotion(
        metrics_champion=metrics_champion,
        metrics_challenger=metrics_challenger,
    )

    # Aggiorniamo i ModelEntry nel registry con le metriche calcolate
    if champion_entry is not None and metrics_champion is not None:
        register_model(
            model_id=champion_entry.model_id,
            model_path=Path(champion_entry.model_path),
            train_dataset_path=ds_path,
            metrics=metrics_champion,
            is_champion=True,
            notes=champion_entry.notes or "Aggiornato da champion_challenger",
        )

    register_model(
        model_id=challenger_entry.model_id,
        model_path=Path(challenger_entry.model_path),
        train_dataset_path=ds_path,
        metrics=metrics_challenger,
        is_champion=decision.promote,
        notes=challenger_entry.notes or "Valutato come challenger",
    )

    ts_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    report = {
        "timestamp_utc": ts_utc,
        "dataset_path": str(ds_path),
        "registry_path": str(REGISTRY_PATH),
        "champion_id": champion_id,
        "challenger_id": challenger_entry.model_id,
        "metrics": {
            "champion": metrics_champion,
            "challenger": metrics_challenger,
        },
        "promotion": {
            "promote": decision.promote,
            "reasons": decision.reasons,
        },
    }

    # Salviamo un report dedicato
    filename = f"champion_challenger_{ts_utc.replace(':', '').replace('-', '')}.json"
    report_path = REPORTS_DIR / filename

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("=== Champion/Challenger ===")
    print(f"Dataset:   {ds_path}")
    print(f"Champion:  {champion_id or 'Nessun champion'}")
    print(f"Challenger:{challenger_entry.model_id}")
    print()
    if metrics_champion is not None:
        print(f"AUC champion:     {metrics_champion['auc']:.3f}")
        print(f"Brier champion:   {metrics_champion['brier']:.3f}")
    else:
        print("Nessun champion: confronto solo per il challenger.")
    print(f"AUC challenger:   {metrics_challenger['auc']:.3f}")
    print(f"Brier challenger: {metrics_challenger['brier']:.3f}")
    print()
    if decision.promote:
        print(">>> Challenger promosso a nuovo champion.")
    else:
        print("Challenger NON promosso. Motivi:")
        for r in decision.reasons:
            print(f"- {r}")

    print()
    print(f"Report salvato in: {report_path}")

    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Champion/Challenger per modello di rischio.")
    parser.add_argument("challenger_id", help="ID del modello challenger nel registry")
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Percorso del dataset CSV da usare per il confronto (default: Gold di progetto)",
    )

    args = parser.parse_args()
    ds_path = Path(args.dataset) if args.dataset else None

    run_champion_challenger(challenger_id=args.challenger_id, dataset_path=ds_path)


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\ml\champion_challenger.py`
- [ ] La funzione `decide_promotion` implementa la logica di promozione
- [ ] La funzione `run_champion_challenger` usa il registry e `evaluate_model_on_dataset`


---

### 2. (Idea di utilizzo) Come usare in pratica il challenger

Per usarlo davvero dovrai avere **almeno due modelli** nel registry:

- un champion (es. `risk_v1`)
- un challenger (es. `risk_v2` addestrato in un momento successivo)

La registrazione del challenger si può fare usando `register_model(...)`
dal REPL o inserendo la chiamata alla fine di `train_risk_model.py`
(quando avrai un nuovo modello).

Userai `run_champion_challenger` per confrontarli sullo stesso dataset.

**Checklist (fine Giorno 4)**
- [ ] Il modulo `champion_challenger` è pronto per essere usato quando avrai un challenger


---

## Giorno 5 – Test su registry e promozione

### Obiettivo del giorno
- Aggiungere test automatici per:
  - `register_model` / `load_registry` con un file fittizio,
  - `decide_promotion` con metriche sintetiche.


---

### 1. Test per `model_registry`

1. In VS Code, nella cartella `tests`, crea il file:

   - `test_model_registry.py`

2. Inserisci questo contenuto:

```python
from pathlib import Path

from src.ml.model_registry import (
    load_registry,
    save_registry,
    register_model,
    get_champion,
    ModelEntry,
)


def test_register_and_get_champion(tmp_path):
    registry_path = tmp_path / "registry.json"

    # Registry vuoto all'inizio
    entries = load_registry(path=registry_path)
    assert entries == []

    # Registriamo un modello come champion
    entry = register_model(
        model_id="risk_test_v1",
        model_path=tmp_path / "risk_test_v1.pkl",
        train_dataset_path=tmp_path / "dataset.csv",
        metrics={"auc": 0.8, "brier": 0.2},
        is_champion=True,
        path=registry_path,
    )

    assert entry.is_champion is True

    champion = get_champion(path=registry_path)
    assert champion is not None
    assert champion.model_id == "risk_test_v1"
```

3. Salva il file.

**Checklist**
- [ ] Esiste `tests/test_model_registry.py` con un test base sul registry


---

### 2. Test per `decide_promotion`

1. In `tests`, crea il file `test_champion_challenger.py`.
2. Inserisci:

```python
from src.ml.champion_challenger import decide_promotion


def test_decide_promotion_promotes_when_better():
    metrics_champion = {"auc": 0.80, "brier": 0.20}
    metrics_challenger = {"auc": 0.82, "brier": 0.20}

    decision = decide_promotion(
        metrics_champion=metrics_champion,
        metrics_challenger=metrics_challenger,
        min_auc_improvement=0.01,
        max_brier_increase=0.0,
    )

    assert decision.promote is True


def test_decide_promotion_rejects_when_auc_not_improved():
    metrics_champion = {"auc": 0.80, "brier": 0.20}
    metrics_challenger = {"auc": 0.80, "brier": 0.19}

    decision = decide_promotion(
        metrics_champion=metrics_champion,
        metrics_challenger=metrics_challenger,
        min_auc_improvement=0.01,
        max_brier_increase=0.01,
    )

    assert decision.promote is False


def test_decide_promotion_rejects_when_brier_too_bad():
    metrics_champion = {"auc": 0.80, "brier": 0.20}
    metrics_challenger = {"auc": 0.82, "brier": 0.25}

    decision = decide_promotion(
        metrics_champion=metrics_champion,
        metrics_challenger=metrics_challenger,
        min_auc_improvement=0.01,
        max_brier_increase=0.0,
    )

    assert decision.promote is False
```

3. Salva il file.

**Checklist**
- [ ] Esiste `tests/test_champion_challenger.py` con test sulla logica di promozione


---

### 3. Eseguire i test

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest tests/test_model_registry.py tests/test_champion_challenger.py
```

Oppure, per tutta la suite:

```bash
pytest
```

Assicurati che i test passino.

**Checklist (fine Giorno 5)**
- [ ] I test di registry e promozione passano
- [ ] Nessun test precedente è stato rotto


---

## Giorno 6 – Documentare “Model registry & champion/challenger”

### Obiettivo del giorno
- Documentare nel `README.md` come usare il registry e il confronto champion/challenger,
- fare un giro completo finale e creare il commit di chiusura Fase 18.


---

### 1. Aggiornare il README

1. Apri `README.md`.
2. Aggiungi una sezione simile (adatta nomi e testo se preferisci):

```markdown
## Model registry & Champion/Challenger

Il modello di rischio utilizza un semplice **model registry** basato su file JSON:

- registry: `models/registry/registry.json`
- API Python: `src/ml/model_registry.py`

Per visualizzare i modelli registrati:

```bash
python -m src.ml.model_registry
```

Ogni entry contiene ID modello, percorso del file `.pkl`, dataset di training,
timestamp e metriche principali (AUC, Brier), oltre a un flag `is_champion`.

Per confrontare un modello **challenger** con il champion corrente e decidere
se promuoverlo viene utilizzato:

- `src/ml/champion_challenger.py`

Esempio di utilizzo:

```bash
python -m src.ml.champion_challenger risk_v2
```

Questo comando:
- valuta champion e challenger sullo stesso dataset Gold,
- calcola le metriche (AUC, Brier),
- applica regole semplici di promozione,
- aggiorna il registry (se il challenger viene promosso),
- salva un report JSON in `data/monitoring/reports/champion_challenger_*.json`.
```

3. Salva il `README.md`.

**Checklist**
- [ ] Il README spiega chiaramente registry e champion/challenger


---

### 2. Giro completo di verifica + commit

1. In locale (opzionale), registra almeno un modello nel registry (es. `risk_v1`).  
2. Esegui i test:

```bash
pytest
```

3. Se tutto è verde, crea il commit:

```bash
git add models/registry/registry.json src/ml/model_registry.py src/ml/champion_challenger.py tests/test_model_registry.py tests/test_champion_challenger.py README.md
git commit -m "Fase 18: model registry e flusso champion/challenger"
git push
```

**Checklist (fine Giorno 6 – fine Fase 18)**
- [ ] Model registry funzionante con almeno un modello registrato
- [ ] Modulo champion/challenger pronto all’uso
- [ ] Test base per registry e promozione
- [ ] README aggiornato
- [ ] Commit Git creato per chiudere la Fase 18


---

Con la Fase 18 hai aggiunto un pezzo fondamentale di **MLOps**:

- puoi tenere traccia di più versioni del modello,
- puoi confrontare champion e challenger su un dataset comune,
- hai una logica chiara (e testata) per decidere quando promuovere un nuovo modello.

Questo completa il quadro insieme al monitoraggio di drift e performance della Fase 17.
