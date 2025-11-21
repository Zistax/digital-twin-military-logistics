# Fase 20 – Runbook operativo & check ops (Parte 2, Giorni 4–6, Windows)

> **Obiettivo pratico (Parte 2)**  
> Mettere nero su bianco **come si gestisce il sistema** dal punto di vista operativo:
>
> - creare un piccolo **runbook operativo** (documento markdown),
> - aggiungere uno script `check_ops` che combina health-check e 1–2 controlli base,
> - aggiornare il `README.md` con un riassunto per chi deve “tenere in piedi” il sistema.


---

## Struttura Fase 20 – Parte 2

- **Giorno 4** – Documento `docs/ops_runbook.md` (avvio, stop, controlli giornalieri)
- **Giorno 5** – Script `check_ops` (health + drift check veloce)
- **Giorno 6** – Sezione “Operatività & Runbook” nel README + commit finale


---

## Giorno 4 – Scrivere il runbook operativo (`docs/ops_runbook.md`)

### Obiettivo del giorno
- Creare un documento testo (Markdown) che spiega:
  - come avviare/fermare l’API,
  - come lanciare la UI Streamlit,
  - quali comandi eseguire per i controlli di routine,
  - dove guardare log e report.


---

### 1. Creare la cartella `docs` (se non esiste)

1. Nella root del progetto, in **VS Code**, crea la cartella:

   - `docs`

Oppure da terminale:

```bash
mkdir docs
```

**Checklist**
- [ ] Esiste la cartella `docs`


---

### 2. Creare il file `docs\ops_runbook.md`

1. Dentro `docs`, crea il file:

   - `ops_runbook.md`

2. Inserisci una struttura di base tipo questa (puoi adattare i testi, ma lascia i comandi):

```markdown
# Runbook operativo – Digital Twin logistico

Questo documento riassume le operazioni principali per avviare, monitorare e
verificare il sistema (API, UI, modello di rischio, simulatore, ecc.).

## 1. Avvio servizi

### 1.1. Attivare ambiente virtuale

Da PowerShell/cmd, nella root del progetto:

```bash
call .venv\Scripts\activate
```

### 1.2. Avviare API FastAPI

```bash
uvicorn src.api.app:app --reload
```

L'API ascolta su `http://127.0.0.1:8000`.

Endpoint utili:

- `/docs` – Swagger UI
- `/health` – health check API
- `/predict` – inferenza rischio
- `/simulate` – simulatore
- `/optimize` – ottimizzazione scenari RL

### 1.3. Avviare UI Streamlit (dashboard principale)

```bash
streamlit run src/ui/dashboard.py
```

### 1.4. Avviare UI di ottimizzazione scenari

```bash
streamlit run src/ui/optimize_app.py
```

---

## 2. Controlli giornalieri

Ogni volta che avvii il sistema (o una volta al giorno), esegui:

1. Health check API:

```bash
check_api_health.bat
```

2. Controllo rapido di drift & metriche modello (se necessario):

```bash
python -m src.ml.run_drift_check
python -m src.ml.retraining_decision
```

3. Verifica che le UI si aprano correttamente nel browser.

---

## 3. Log e report

- **Log API**: `logs/api/api.log`
- **Report drift & performance modello**: `data/monitoring/reports/drift_*.json` e `drift_latest.json`
- **Report retraining**: `data/monitoring/reports/retrain_*.json`
- **Report champion/challenger**: `data/monitoring/reports/champion_challenger_*.json`

In caso di problemi, controllare prima:

1. che l'API sia su (`/health` e `api.log`);
2. che non ci siano errori evidenti nei log;
3. che i report di drift non mostrino cali drastici di AUC o PSI molto alto.

---

## 4. Prima di una nuova versione del modello

Riassunto dei passi principali:

1. Eseguire drift check e decisione retraining:

```bash
python -m src.ml.run_drift_check
python -m src.ml.retraining_decision
```

2. Se consigliato, lanciare il retraining:

```bash
python -m src.ml.retrain_pipeline --run-champion-challenger
```

3. Verificare:

   - aggiornamento del model registry (`python -m src.ml.model_registry`),
   - eventuale promozione del nuovo modello a champion,
   - qualità delle metriche nel report champion/challenger.

4. Annotare nel registro interno (anche solo un file markdown o note personali)
   la data e il motivo dell'aggiornamento.
```

3. Salva il file.

**Checklist (fine Giorno 4)**
- [ ] Esiste `docs/ops_runbook.md` con istruzioni di avvio e controlli
- [ ] Il runbook elenca comandi chiave (/health, drift, retrain, ecc.)


---

## Giorno 5 – Script `check_ops` (health + drift veloce)

### Obiettivo del giorno
- Creare uno script che faccia un piccolo **“giro di controllo”**:

  1. chiama `/health` tramite `check_api_health`,
  2. esegue `run_drift_check` in modalità “veloce” (solo stampa),
  3. stampa a schermo un riassunto finale (OK / WARNING).


> Nota: per semplicità, lo script userà direttamente le funzioni Python già
> definite, così eviti di combinare sottoprocessi complicati.


---

### 1. Creare `src\tools\check_ops.py`

1. In **VS Code**, nella cartella `src/tools`, crea il file:

   - `check_ops.py`

2. Inserisci questo contenuto:

```python
from __future__ import annotations

from typing import Dict

from src.tools.check_api_health import check_api_health
from src.ml.run_drift_check import run_drift_check


def check_ops() -> int:
    """Esegue un controllo operativo base (health + drift).

    Ritorna 0 se tutto OK, 1 se ci sono warning/errori evidenti.
    """
    exit_code = 0

    print("=== OPS CHECK ===")

    # 1) Health API
    print("
[1/2] Health check API")
    health_exit = check_api_health()
    if health_exit != 0:
        print(">> Health check API NON OK.")
        exit_code = 1
    else:
        print(">> Health check API OK.")

    # 2) Drift check (usiamo il run_drift_check esistente)
    print("
[2/2] Drift check (vedi dettagli sopra)")
    try:
        psi_by_feature: Dict[str, float] = run_drift_check()
        max_psi = max(psi_by_feature.values()) if psi_by_feature else 0.0
        print(f"
PSI massimo: {max_psi:.3f}")
        if max_psi > 0.2:
            print(">> ATTENZIONE: drift significativo (PSI > 0.2).")
            exit_code = 1
        elif max_psi > 0.1:
            print(">> WARNING: drift moderato (PSI > 0.1).")
            # Non cambiamo exit_code in questo caso, ma segnaliamo.
        else:
            print(">> Drift sotto soglia critica.")
    except Exception as exc:  # noqa: PERF203
        print(f">> ERRORE durante drift check: {exc}")
        exit_code = 1

    print("
=== RISULTATO FINALE OPS CHECK ===")
    if exit_code == 0:
        print("Tutto OK (nessun problema critico rilevato).")
    else:
        print("Ci sono problemi o warning importanti (vedi messaggi sopra).")

    return exit_code


def main() -> None:
    import sys

    code = check_ops()
    sys.exit(code)


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/tools/check_ops.py` con `check_ops()` e `main()`


---

### 2. (Opzionale) Creare `check_ops.bat`

1. Nella root del progetto, crea il file:

   - `check_ops.bat`

2. Inserisci:

```bat
@echo off
call .venv\Scripts\activate
python -m src.tools.check_ops
```

3. Salva il file.

**Checklist**
- [ ] Esiste `check_ops.bat` (opzionale, ma comodo)


---

### 3. Prova del check operativo

1. Assicurati che l’API sia in esecuzione:

```bash
uvicorn src.api.app:app --reload
```

2. In un altro terminale (con `.venv` attivo), lancia:

```bash
python -m src.tools.check_ops
```

oppure, se hai creato il `.bat`:

```bash
check_ops.bat
```

Dovresti vedere:

- la sezione del health-check (uguale a `check_api_health`),
- la sezione del drift check (output di `run_drift_check`),
- il riepilogo finale.

**Checklist (fine Giorno 5)**
- [ ] `python -m src.tools.check_ops` gira senza errori
- [ ] In caso di PSI alto o health non OK, lo script segnala chiaramente il problema


---

## Giorno 6 – Aggiornare README con “Operatività & Runbook”

### Obiettivo del giorno
- Aggiungere una sezione nel `README.md` che spieghi:
  - dove trovare il runbook,
  - quali script usare per i controlli operativi,
  - quali log/dir sono importanti.


---

### 1. Aggiornare `README.md`

1. Apri `README.md`.
2. Aggiungi una sezione simile (adatta il testo come preferisci):

```markdown
## Operativita' & Runbook

Le istruzioni operative dettagliate sono in:

- `docs/ops_runbook.md`

Strumenti principali per il controllo dello stato del sistema:

- **Health API**  
  ```bash
  check_api_health.bat
  ```  
  oppure:  
  ```bash
  python -m src.tools.check_api_health
  ```

- **Drift & performance check**  
  ```bash
  python -m src.ml.run_drift_check
  python -m src.ml.retraining_decision
  ```

- **Retraining + confronto champion/challenger**  
  ```bash
  python -m src.ml.retrain_pipeline --run-champion-challenger
  ```

- **OPS check combinato (health + drift rapido)**  
  ```bash
  check_ops.bat
  ```  
  oppure:  
  ```bash
  python -m src.tools.check_ops
  ```

Log e report utili:

- log API: `logs/api/api.log`
- report drift: `data/monitoring/reports/drift_*.json`, `drift_latest.json`
- report retraining: `data/monitoring/reports/retrain_*.json`
- report champion/challenger: `data/monitoring/reports/champion_challenger_*.json`
```

3. Salva il `README.md`.

**Checklist**
- [ ] Il README punta chiaramente a `docs/ops_runbook.md`
- [ ] Sono elencati gli script di controllo (`check_api_health`, `check_ops`, ecc.)


---

### 2. Giro finale e commit di Fase 20

1. (Facoltativo) Esegui un giro di controlli:

```bash
check_api_health.bat
check_ops.bat
```

2. Esegui la suite di test (almeno una volta dopo le modifiche):

```bash
pytest
```

3. Se tutto è ok, crea il commit:

```bash
git add src/api/app.py src/api/logging_setup.py src/tools/__init__.py src/tools/check_api_health.py src/tools/check_ops.py docs/ops_runbook.md README.md check_api_health.bat check_ops.bat
git commit -m "Fase 20: health check, logging operativo e runbook ops"
git push
```

**Checklist (fine Giorno 6 – fine Fase 20)**
- [ ] Endpoint `/health` e script `check_api_health` funzionanti
- [ ] Logging API su file `logs/api/api.log`
- [ ] Script `check_ops` per controllo operativo rapido
- [ ] Runbook operativo scritto in `docs/ops_runbook.md`
- [ ] README aggiornato e commit creato per chiudere la Fase 20


---

Con la Fase 20 hai aggiunto un livello importante di **operatività**:

- controlli rapidi sullo stato del sistema,
- log centralizzati per l’API,
- un documento che spiega chiaramente cosa fare per avviare, monitorare e verificare
  il digital twin logistico nel tempo.
