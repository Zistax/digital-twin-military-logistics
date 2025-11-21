# Fase 23 – Circuit breaker, retention & licensing (Parte 2, Giorni 4–6, Windows)

> **Obiettivo pratico (Parte 2)**  
> Completare il quadro di **governance & etica** con tre elementi:
>
> - un semplice **circuit breaker** basato su drift/performance,
> - config di **retention** per log/report (almeno come job manuale/documentato),
> - impostare il **licensing** del progetto (Apache-2.0 per il core).


---

## Struttura Fase 23 – Parte 2

- **Giorno 4** – Circuit breaker basato su drift/performance
- **Giorno 5** – Retention log/report (script manuale + documentazione)
- **Giorno 6** – Licensing (LICENSE, header opzionali) + README


---

## Giorno 4 – Circuit breaker basato su drift/performance

### Obiettivo del giorno
- Creare una funzione che legge l’ultimo report di drift & performance,
- se trova condizioni **critiche**, segnala che il sistema è “degraded”,
- usare questo stato in `/health` (o in altri punti).


---

### 1. Creare `src\ml\circuit_breaker.py`

1. In **VS Code**, nella cartella `src/ml`, crea il file:

   - `circuit_breaker.py`

2. Inserisci il seguente codice:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


DRIFT_LATEST_PATH = Path("data") / "monitoring" / "reports" / "drift_latest.json"


@dataclass
class CircuitBreakerState:
    degraded: bool
    reasons: list[str]


def load_drift_latest(path: Path = DRIFT_LATEST_PATH) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_circuit_breaker(
    drift_report: Dict[str, Any] | None,
    psi_threshold: float = 0.3,
    auc_drop_threshold: float = -0.1,
    brier_increase_threshold: float = 0.05,
) -> CircuitBreakerState:
    """Applica regole semplici per capire se lo stato e' degraded.

    - drift_report: tipicamente il contenuto di drift_latest.json
    - psi_threshold: se qualche PSI > 0.3 -> degraded
    - auc_drop_threshold: se delta AUC <= -0.1 -> degraded
    - brier_increase_threshold: se delta Brier >= +0.05 -> degraded
    """
    reasons: list[str] = []
    degraded = False

    if drift_report is None:
        # Nessun dato: non blocchiamo, ma potresti volerlo considerare un warning.
        return CircuitBreakerState(degraded=False, reasons=["no_drift_report"])

    psi_by_feature = drift_report.get("psi_by_feature", {})
    if isinstance(psi_by_feature, dict):
        worst_psi = max(psi_by_feature.values()) if psi_by_feature else 0.0
        if worst_psi > psi_threshold:
            degraded = True
            reasons.append(f"psi_above_threshold:{worst_psi:.3f}>{psi_threshold:.3f}")

    metrics = drift_report.get("metrics", {})
    if isinstance(metrics, dict):
        auc_ref = float(metrics.get("auc_ref", 0.0))
        auc_cur = float(metrics.get("auc_cur", 0.0))
        brier_ref = float(metrics.get("brier_ref", 1.0))
        brier_cur = float(metrics.get("brier_cur", 1.0))

        delta_auc = auc_cur - auc_ref
        delta_brier = brier_cur - brier_ref

        if delta_auc <= auc_drop_threshold:
            degraded = True
            reasons.append(f"auc_drop:{delta_auc:.3f}<={auc_drop_threshold:.3f}")

        if delta_brier >= brier_increase_threshold:
            degraded = True
            reasons.append(f"brier_increase:{delta_brier:.3f}>={brier_increase_threshold:.3f}")

    return CircuitBreakerState(degraded=degraded, reasons=reasons)
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/ml/circuit_breaker.py` con `CircuitBreakerState` ed `evaluate_circuit_breaker`


---

### 2. Integrare il circuito in `/health`

1. Apri `src/api/app.py`.
2. Aggiungi gli import:

```python
from src.ml.circuit_breaker import load_drift_latest, evaluate_circuit_breaker
```

3. Nell’endpoint `/health`, dopo aver determinato `model_version`, aggiungi:

```python
    drift_report = load_drift_latest()
    cb_state = evaluate_circuit_breaker(drift_report)

    status = "ok"
    if model_version is None or cb_state.degraded:
        status = "degraded"
```

4. Aggiorna anche il campo `details` in modo da includere le ragioni (se presenti):

```python
    return HealthResponse(
        status=status,
        version=model_version,
        details={
            "service": "risk_api",
            "time_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "circuit_breaker_reasons": cb_state.reasons,
        },
    )
```

5. Salva il file.

**Checklist**
- [ ] `/health` tiene conto dello stato del circuit breaker
- [ ] In caso di drift/performance gravi, `status` diventa `degraded` e `details` mostra le ragioni


---

### 3. Test manuale del circuit breaker

1. Esegui almeno una volta il drift check:

```bash
python -m src.ml.run_drift_check
```

2. (Opzionale) Modifica temporaneamente `drift_latest.json` per simulare valori
   pessimi (PSI alto, AUC drop forte), salvando il file.

3. Avvia l’API:

```bash
uvicorn src.api.app:app --reload
```

4. Chiama `/health`:

```bash
python -m src.tools.check_api_health
```

5. Verifica che in caso di condizioni critiche `status` sia `degraded` e che
   `circuit_breaker_reasons` contenga le motivazioni.

**Checklist (fine Giorno 4)**
- [ ] Circuit breaker integrato in `/health` e verificato manualmente


---

## Giorno 5 – Retention log/report

### Obiettivo del giorno
- Definire una **retention** minima per log/report (365+ giorni a scopo audit),
- creare uno script semplice che “pulisce” file troppo vecchi,
- documentare come e quando usarlo (non serve scheduling automatico per ora).


---

### 1. Creare `src\tools\retention_cleanup.py`

1. In **VS Code**, nella cartella `src/tools`, crea il file:

   - `retention_cleanup.py`

2. Inserisci:

```python
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List


LOG_DIRS = [
    Path("logs") / "api",
    Path("logs") / "audit",
]

REPORT_DIR = Path("data") / "monitoring" / "reports"


def iter_files(dirs: Iterable[Path]) -> Iterable[Path]:
    for d in dirs:
        if not d.exists():
            continue
        for root, _, files in os.walk(d):
            root_path = Path(root)
            for name in files:
                yield root_path / name


def delete_older_than(days: int = 365) -> List[Path]:
    """Cancella file più vecchi di `days` nelle cartelle configurate.

    Ritorna la lista di file cancellati.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    deleted: List[Path] = []

    for path in iter_files(LOG_DIRS + [REPORT_DIR]):
        try:
            mtime = datetime.utcfromtimestamp(path.stat().st_mtime)
        except OSError:
            continue

        if mtime < cutoff:
            try:
                path.unlink()
                deleted.append(path)
            except OSError:
                continue

    return deleted


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Pulizia file di log/report più vecchi di N giorni.")
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Soglia di retention in giorni (default: 365)",
    )

    args = parser.parse_args()

    deleted = delete_older_than(days=args.days)
    print(f"File cancellati ({len(deleted)}):")
    for p in deleted:
        print(f"- {p}")


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/tools/retention_cleanup.py` con `delete_older_than` e `main()`


---

### 2. Uso manuale della retention

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python -m src.tools.retention_cleanup --days 365
```

2. Controlla l’elenco dei file cancellati (se ce ne sono).

3. **Nota importante:** per ora è uno script manuale.  
   Se un giorno userai un job scheduler (es. Windows Task Scheduler), potrai farlo girare
   una volta al mese con il comando sopra.

**Checklist (fine Giorno 5)**
- [ ] Script retention testato manualmente
- [ ] Hai chiaro che la retention non è automatica ma manuale/programmazione esterna


---

## Giorno 6 – Licensing (Apache-2.0) & README

### Obiettivo del giorno
- Aggiungere il file **LICENSE** con testo Apache-2.0,
- indicare nel README il modello di licensing (core Apache, plugin eventuali proprietari),
- opzionale: aggiungere un breve header nei file principali.


---

### 1. Aggiungere il file LICENSE (Apache-2.0)

1. Nella root del progetto, crea un file:

   - `LICENSE`

2. Inserisci il testo della licenza Apache-2.0.  
   Puoi copiare il testo standard (va bene anche una versione sintetica purché contenga
   i termini principali).

3. Adatta l’intestazione con il tuo nome / organizzazione e l’anno corrente.

**Checklist**
- [ ] Esiste `LICENSE` nella root con testo Apache-2.0


---

### 2. Aggiornare il README con sezione Licensing

1. Apri `README.md`.
2. Aggiungi una sezione, ad esempio verso il fondo:

```markdown
## Licensing

Il core del progetto (codice in `src/`, file di configurazione in `conf/` e strumenti
in `src/tools/`) è rilasciato sotto licenza **Apache-2.0** (vedi file `LICENSE`).

Eventuali connettori specifici, integrazioni proprietarie o componenti non inclusi
in questo repository possono essere soggetti a licenze diverse (es. proprietarie).
```

3. Salva il file.

**Checklist**
- [ ] Il README descrive chiaramente lo schema di licensing


---

### 3. (Opzionale) Intestazione di licensing nei file principali

> Non è strettamente necessario, ma può essere utile per chiarezza.

1. Scegli 2–3 file core (es. `src/api/app.py`, `src/ml/train_risk_model.py`) e, in testa,
   aggiungi un breve commento del tipo:

```python
# Copyright (c) 2025 <TUO NOME / ORGANIZZAZIONE>
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http(s)://www.apache.org/licenses/LICENSE-2.0
```

2. Salva i file.

**Checklist**
- [ ] Alcuni file chiave riportano un header di licensing (se lo desideri)


---

### 4. Giro finale & commit Fase 23

1. Esegui la suite di test:

```bash
pytest
```

2. Prova i componenti aggiunti:

- `/health` → controlla `status` e `circuit_breaker_reasons`,
- `python -m src.tools.retention_cleanup --days 365` (anche solo a secco),
- verifica che `LICENSE` sia nella root.

3. Se tutto ok, crea il commit:

```bash
git add src/api/pii_sanitizer.py src/config/terminology.py conf/ops/terminology.yml src/api/audit_logging.py src/ml/circuit_breaker.py src/tools/retention_cleanup.py LICENSE README.md docs/security_notes.md
git commit -m "Fase 23: etica, terminologia, circuit breaker e licensing"
git push
```

**Checklist (fine Giorno 6 – fine Fase 23)**
- [ ] Circuit breaker operativo agganciato a `/health`
- [ ] Script retention pronto per evitare log/report infiniti
- [ ] Licensing Apache-2.0 impostato e documentato
- [ ] Elementi base di etica/governance (PII, terminologia, audit) integrati


---

Con la Fase 23 hai consolidato gli aspetti di **etica, governance e conformità leggera**:

- riduci il rischio di log con PII,
- hai terminologia configurabile per diversi tenant,
- disponi di audit log, circuit breaker e retention logica,
- il progetto è chiaramente licenziato e pronto per essere condiviso o esteso.
