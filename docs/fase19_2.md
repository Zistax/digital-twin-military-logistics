# Fase 19 – Retraining pipeline (Parte 2, Giorni 4–6, Windows)

> **Obiettivo pratico (Parte 2)**  
> Collegare la pipeline di retraining al flusso **champion/challenger** e al
> monitoraggio, in modo da avere un workflow quasi completo:
>
> - (opzionale) controllare prima il drift (`run_drift_check` + `retraining_decision`),
> - lanciare il retraining (`retrain_pipeline`),
> - confrontare champion e challenger (`champion_challenger`),
> - aggiornare il registry e la documentazione.


---

## Struttura Fase 19 – Parte 2

- **Giorno 4** – Integrare `retrain_pipeline` con champion/challenger (flag CLI)
- **Giorno 5** – Aggiungere test base sulla pipeline (parte logica)
- **Giorno 6** – Documentare il workflow “Drift → Retrain → Champion/Challenger” nel README


---

## Giorno 4 – Integrare `retrain_pipeline` con champion/challenger


### Obiettivo del giorno
- Aggiungere alla CLI di `retrain_pipeline` un flag opzionale:
  - `--run-champion-challenger`  
  che, alla fine del retraining, lancia automaticamente il confronto con il champion.


---

### 1. Modificare `retrain_pipeline.py` per importare `run_champion_challenger`

1. Apri `src/ml/retrain_pipeline.py`.
2. In testa al file, aggiungi l’import:

```python
from src.ml.champion_challenger import run_champion_challenger
```

Assicurati che la riga sia vicino agli altri import di `src.ml.*`.

**Checklist**
- [ ] `retrain_pipeline.py` importa `run_champion_challenger`


---

### 2. Estendere la CLI con il flag `--run-champion-challenger`

1. Nella funzione `main()` di `retrain_pipeline.py`, modifica il parser aggiungendo un argomento:

Cerca:

```python
    parser = argparse.ArgumentParser(
        description="Pipeline di retraining del modello di rischio."
    )
```

Subito dopo, aggiungi:

```python
    parser.add_argument(
        "--run-champion-challenger",
        action="store_true",
        help=(
            "Se specificato, dopo il retraining esegue anche il confronto "
            "champion/challenger usando il nuovo modello come challenger."
        ),
    )
```

2. Dopo che hai ottenuto `args` e `ds_path` e hai eseguito:

```python
    report = run_retrain_pipeline(dataset_path=ds_path)
```

aggiungi il blocco:

```python
    if args.run_champion_challenger:
        print()
        print("Eseguo confronto champion/challenger con il nuovo modello...")
        from_model_id = report.get("model_id")
        if not from_model_id:
            print("Attenzione: nessun model_id nel report di retraining, salto il confronto.")
        else:
            # Usiamo lo stesso dataset della run per il confronto
            cc_report = run_champion_challenger(
                challenger_id=from_model_id,
                dataset_path=ds_path,
            )
            # Possiamo anche arricchire il report di retraining con qualche info
            report["champion_challenger"] = {
                "champion_id": cc_report.get("champion_id"),
                "challenger_id": cc_report.get("challenger_id"),
                "promotion": cc_report.get("promotion"),
            }
```

3. Lascia **invariata** la parte che salva il report JSON (`retrain_*.json`), ma ora
   verrà salvato un report più ricco se hai usato il flag.

**Checklist**
- [ ] La CLI di `retrain_pipeline` accetta `--run-champion-challenger`
- [ ] Se il flag è usato, viene chiamato `run_champion_challenger(...)`
- [ ] Il report finale include, se presente, una sezione `champion_challenger`


---

### 3. Prova pratica: retrain + champion/challenger in un colpo solo

1. Nel terminale, dalla root del progetto:

   ```bash
   python -m src.ml.retrain_pipeline --run-champion-challenger
   ```

2. Osserva l’output:
   - prima la parte di training,
   - poi la stampa delle metriche AUC/Brier del nuovo modello,
   - infine l’output della parte champion/challenger (promosso o no).

3. Apri l’ultimo `retrain_*.json` in `data/monitoring/reports` e verifica che contenga anche:

   ```json
   "champion_challenger": {
     "champion_id": "...",
     "challenger_id": "...",
     "promotion": {
       "promote": true/false,
       "reasons": [...]
     }
   }
   ```

**Checklist (fine Giorno 4)**
- [ ] `python -m src.ml.retrain_pipeline --run-champion-challenger` funziona
- [ ] Il registry è aggiornato con il nuovo modello (champion o challenger)
- [ ] Il report di retraining contiene le info di champion/challenger


---

## Giorno 5 – Test base sulla pipeline (parte logica)


### Obiettivo del giorno
- Aggiungere almeno un test automatico “leggero” sulla parte logica di `retrain_pipeline`,
- senza rieseguire davvero tutto il training pesante in test.

> L’idea è verificare che `run_retrain_pipeline`:
> - fallisca con dataset inesistente,
> - costruisca i percorsi giusti,
> - chiami le funzioni principali (in modo controllato, se le fingi/mokki).


---

### 1. Creare `tests/test_retrain_pipeline.py` (test semplice sul dataset inesistente)

1. In **VS Code**, nella cartella `tests`, crea il file:

   - `test_retrain_pipeline.py`

2. Inserisci un primo test semplice:

```python
from pathlib import Path

import pytest

from src.ml.retrain_pipeline import run_retrain_pipeline


def test_run_retrain_pipeline_raises_if_dataset_missing(tmp_path):
    # Usiamo un percorso fittizio dentro tmp_path
    fake_dataset = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        run_retrain_pipeline(dataset_path=fake_dataset)
```

> Questo test è molto leggero ma utile: garantisce che ci sia un controllo chiaro
> sull’esistenza del dataset prima del training.

3. Salva il file.

**Checklist**
- [ ] Esiste `tests/test_retrain_pipeline.py` con almeno un test base


---

### 2. Eseguire i test

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest tests/test_retrain_pipeline.py
```

Oppure, per tutta la suite:

```bash
pytest
```

Assicurati che i test passino (e che non si rompano quelli già esistenti).

**Checklist (fine Giorno 5)**
- [ ] Il test su `run_retrain_pipeline` passa
- [ ] Nessun test precedente è in errore


---

## Giorno 6 – Documentare il workflow Drift → Retrain → Champion/Challenger


### Obiettivo del giorno
- Aggiungere nel `README.md` una sezione che spieghi passo-passo il flusso completo:
  - controllo drift,
  - decisione di retraining,
  - retraining pipeline,
  - confronto champion/challenger.


---

### 1. Aggiornare il README con il workflow end-to-end

1. Apri `README.md`.
2. Aggiungi (o completa) una sezione, ad esempio subito dopo “Monitoraggio modello & Drift”:

```markdown
## Workflow Drift → Retraining → Champion/Challenger

Il ciclo di vita del modello di rischio segue un flusso manuale ma strutturato:

1. **Drift & performance check**  
   ```bash
   python -m src.ml.run_drift_check
   ```

   Questo comando calcola il PSI per le feature e valuta il modello corrente su
   dataset di riferimento e corrente, salvando un report in
   `data/monitoring/reports/drift_latest.json`.

2. **Decisione di retraining**  
   ```bash
   python -m src.ml.retraining_decision
   ```

   Legge `drift_latest.json` e, in base a soglie di PSI/AUC/Brier, suggerisce se
   è consigliato pianificare un nuovo training del modello.

3. **Retraining del modello (nuovo challenger)**  
   ```bash
   python -m src.ml.retrain_pipeline
   ```

   Allena un nuovo modello di rischio usando il dataset corrente (o un dataset
   specificato con `--dataset`), salva il modello con nome versionato in
   `models/risk_model_*.pkl`, lo registra nel model registry come *challenger* e
   salva un report della run in `data/monitoring/reports/retrain_*.json`.

4. **Confronto Champion/Challenger e promozione opzionale**  
   ```bash
   python -m src.ml.retrain_pipeline --run-champion-challenger
   ```

   Oltre al retraining, esegue anche il confronto tra champion e nuovo
   challenger tramite `champion_challenger.py`, aggiornando il registry (se il
   challenger viene promosso) e arricchendo il report di retraining con le
   informazioni di promozione.
```

3. Salva il `README.md`.

**Checklist**
- [ ] Il README descrive chiaramente il flusso Drift → Retrain → Champion/Challenger


---

### 2. Giro finale di verifica e commit

1. (Opzionale) Rigenera un report di drift:

   ```bash
   python -m src.ml.run_drift_check
   python -m src.ml.retraining_decision
   ```

2. Esegui un retraining completo con promozione opzionale:

   ```bash
   python -m src.ml.retrain_pipeline --run-champion-challenger
   ```

3. Esegui i test:

   ```bash
   pytest
   ```

4. Se tutto è ok, crea il commit di fine Fase 19:

   ```bash
   git add src/ml/retrain_pipeline.py tests/test_retrain_pipeline.py README.md
   git commit -m "Fase 19: retraining pipeline e integrazione con champion/challenger"
   git push
   ```

**Checklist (fine Giorno 6 – fine Fase 19)**
- [ ] Pipeline `retrain_pipeline` funzionante e testata
- [ ] Integrazione con champion/challenger tramite flag CLI
- [ ] README aggiornato con workflow completo
- [ ] Commit Git creato per chiudere la Fase 19


---

Con la Fase 19 hai trasformato i tasselli precedenti (drift, decisione di retraining,
model registry, champion/challenger) in un **workflow operativo**:

- controlli se il modello sta invecchiando sui dati nuovi,
- se serve, lanci il retraining,
- confronti in modo strutturato il nuovo modello con quello in produzione (champion),
- decidi consapevolmente se promuoverlo, con traccia di tutto nei report JSON.
