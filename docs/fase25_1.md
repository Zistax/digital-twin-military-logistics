# Fase 25 – Demo finale & Manuale d’uso (Parte 1, Giorni 1–3, Windows)

> **Obiettivo pratico (Parte 1)**  
> Preparare una **demo end‑to‑end** e la documentazione “umana” di base:
>
> - manuale per il ruolo **Planner**,
> - manuale per il ruolo **Analyst**,
> - documento di **demo guidata** con i comandi in sequenza.
>
> L’idea è che, alla fine della fase, tu (o qualcun altro) possiate:
> - accendere l’ambiente,
> - seguire i passaggi di una demo,
> - capire cosa fa il sistema senza leggere il codice.


---

## Struttura Fase 25 – Parte 1

- **Giorno 1** – Manuale Planner (`docs/user_guide_planner.md`)
- **Giorno 2** – Manuale Analyst (`docs/user_guide_analyst.md`)
- **Giorno 3** – Demo end‑to‑end (`docs/runbook_end_to_end_demo.md`) + opzionale `demo_all_in_one.bat`


---

## Giorno 1 – Manuale Planner

### Obiettivo del giorno
- Scrivere un **manuale operativo** per il ruolo Planner:
  - come avviare API e UI,
  - come creare/gestire una missione (convogli, parametri, scenari),
  - come leggere i suggerimenti di rischio / RL,
  - come registrare le decisioni operative (anche solo concettualmente).


---

### 1. Creare (se serve) la cartella `docs`

1. In Esplora File o VS Code, nella root del progetto, verifica se esiste la cartella `docs`.
2. Se non esiste, creala:

```bash
mkdir docs
```

**Checklist**
- [ ] La cartella `docs` esiste nella root del progetto


---

### 2. Creare `docs\user_guide_planner.md`

1. In VS Code, nella cartella `docs`, crea il file:

   - `user_guide_planner.md`

2. Inserisci una struttura simile (puoi personalizzare i dettagli):

```markdown
# Guida Planner – Digital Twin logistico

## 1. Scopo del sistema

Questo strumento aiuta il Planner a:

- configurare missioni di convogli,
- stimare il rischio prima della partenza e in corso di missione,
- confrontare scenari alternativi,
- ricevere suggerimenti di manovra (azioni RL) da confermare/modificare.

## 2. Avvio rapido (da Windows)

1. Apri `cmd` o PowerShell nella cartella del progetto.
2. Attiva l'ambiente virtuale:

   ```bash
   call .venv\Scripts\activate
   ```

3. Avvia l'API:

   ```bash
   uvicorn src.api.app:app --reload
   ```

4. In un altro terminale, sempre con `.venv` attivo, avvia la dashboard:

   ```bash
   streamlit run src/ui/dashboard.py
   ```

5. Apri il browser su `http://localhost:8501` (dashboard) e `http://127.0.0.1:8000/docs` (API docs).

## 3. Creare una missione (scenario base)

1. Nella dashboard, vai nella sezione "Simulazione" o equivalente.
2. Imposta i parametri principali (esempi):
   - numero convogli (es. 3–5),
   - durata simulazione,
   - configurazione deposito (capacità),
   - eventuale scenario meteo/traffico (se disponibile).
3. Avvia la simulazione e attendi il completamento.
4. Verifica che i risultati compaiano nella sezione KPI (tempo medio, failure, ecc.).

## 4. Valutare il rischio pre‑partenza

1. Per ogni missione/convoglio, seleziona i dati di scenario.
2. Usa il pulsante o la sezione "Predizione rischio" (API `/predict` sotto la UI).
3. Osserva:
   - probabilità stimata di failure,
   - classe di rischio (basso/medio/alto),
   - soglia utilizzata (es. 0.7).
4. Se la probabilità è molto alta, valuta alternative:
   - ridurre numero convogli,
   - cambiare route,
   - modificare l’orario di partenza.

## 5. Suggerimenti RL e decisioni Planner

1. Nella sezione "Ottimizzazione" o simile, lancia un suggerimento RL (`/optimize`).
2. Il sistema propone una o più azioni, ad esempio:
   - cambiare waypoint,
   - introdurre un hold (pausa controllata),
   - richiedere un escort, ecc.
3. Come Planner:
   - **conferma** il suggerimento se coerente con le regole operative,
   - **modifica** l’azione se ritieni che il contesto reale sia diverso,
   - **rifiuta** se non applicabile.
4. Le decisioni confermate/modificate vengono registrate in `logs/audit/decisions.log`
   (permette analisi future su quanto RL e Planner sono allineati).

## 6. Cosa controllare prima di una missione reale

- Stato `/health` dell’API: deve essere `ok` o, al massimo, `degraded` ma sotto controllo.
- Drift dei dati: nessun PSI "fuori scala" per le feature critiche.
- Soglie di rischio: verificate insieme all’Analyst (vedi guida Analyst).
- Log operativi puliti: nessun errore grave nelle ultime esecuzioni.

## 7. Riferimenti

- Guida Analyst: `docs/user_guide_analyst.md`
- Runbook operativo: `docs/ops_runbook.md`
- Note di sicurezza: `docs/security_notes.md`
```

3. Salva il file.

**Checklist**
- [ ] Esiste `docs/user_guide_planner.md` con una struttura simile a quella proposta
- [ ] La guida spiega come avviare API + UI e usare simulazione/predizione/ottimizzazione


---

## Giorno 2 – Manuale Analyst

### Obiettivo del giorno
- Scrivere un manuale operativo per il ruolo **Analyst**:
  - come leggere KPI e report,
  - come usare drift, SLO e retraining decision,
  - come collaborare con il Planner.


---

### 1. Creare `docs\user_guide_analyst.md`

1. In VS Code, nella cartella `docs`, crea il file:

   - `user_guide_analyst.md`

2. Inserisci una struttura simile:

```markdown
# Guida Analyst – Digital Twin logistico

## 1. Scopo del ruolo

L'Analyst ha il compito di:

- controllare la qualita' del modello di rischio,
- monitorare il drift dei dati e delle performance,
- proporre (o meno) il retraining del modello,
- tarare soglie e alert insieme al Planner.

## 2. Avvio strumenti principali

1. Assicurati che l'ambiente `.venv` sia attivo.
2. Per l'API e la UI, vedi la Guida Planner.
3. Per l'analisi offline, concentrati sugli script in `src/ml` e `src/tools`.

## 3. Controllo drift & performance

Per verificare drift e performance del modello:

```bash
python -m src.ml.run_drift_check
```

- genera o aggiorna i report in `data/monitoring/reports` (es. `drift_latest.json`),
- produce un riepilogo (PSI per feature, delta AUC/Brier).

Per una verifica più sintetica, usa:

```bash
python -m src.tools.check_ops
```

che combina:
- health check API,
- drift check,
- eventuali SLO di latenza.

## 4. Verifica SLO di latenza

Per verificare che gli SLO di latenza siano rispettati:

```bash
python -m src.tools.api_latency_stats
python -m src.tools.check_slo
```

- `api_latency_stats`: calcola media e p95 per endpoint (dai log API),
- `check_slo`: confronta i valori con quanto definito in `conf/ops/slo.yml`.

## 5. Decisione di retraining

Per stimare se è il caso di retrainare il modello di rischio:

```bash
python -m src.ml.retraining_decision
```

Il comando utilizza le regole configurate (drift, AUC, Brier) e restituisce un esito
(es. "RETRAIN_NEEDED" vs "NO_RETRAIN").

Se la decisione è di retrain:

```bash
python -m src.ml.retrain_pipeline --run-champion-challenger
```

- allena un nuovo modello challenger,
- confronta con il champion attuale,
- salva i report e, se previsto, aggiorna il modello servito.

## 6. Lavoro con il Planner

- Condividi periodicamente al Planner:
  - andamento dei KPI (failure rate, tempo medio, ecc.),
  - eventuali drift significativi,
  - cambi di soglia (es. da 0.7 a 0.65 per high‑risk).
- Prima di un retraining che cambia molto il comportamento del modello,
  valuta di fare una demo interna con scenari tipici.

## 7. Pulizia log & retention

- Per evitare che log e report crescano all'infinito, puoi usare:

  ```bash
  python -m src.tools.retention_cleanup --days 365
  ```

- Vedi anche `docs/security_notes.md` per le parti di sicurezza/retention.

```

3. Salva il file.

**Checklist**
- [ ] Esiste `docs/user_guide_analyst.md`
- [ ] La guida spiega chiaramente come usare drift check, SLO, retraining_decision e retention


---

## Giorno 3 – Demo end‑to‑end documentata

### Obiettivo del giorno
- Scrivere un documento che descrive un **percorso completo**: da zero a demo,
- opzionale: creare uno script `.bat` per avviare i pezzi principali.


---

### 1. Creare `docs\runbook_end_to_end_demo.md`

1. In VS Code, nella cartella `docs`, crea il file:

   - `runbook_end_to_end_demo.md`

2. Inserisci una struttura come la seguente (puoi adattare in base a come hai fatto il progetto):

```markdown
# Runbook demo end-to-end – Digital Twin logistico

Questo documento descrive una demo "tipo" da eseguire in 30–60 minuti,
partendo da un ambiente locale con il repository gia' clonato.

## 1. Preparazione ambiente

1. Apri un terminale nella cartella del progetto.
2. Attiva `.venv`:

   ```bash
   call .venv\Scripts\activate
   ```

3. (Se necessario) aggiorna le dipendenze:

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. Verifica che i test base passino:

   ```bash
   pytest
   ```

## 2. Esecuzione simulazione di esempio

1. Lancia una simulazione standard:

   ```bash
   python -m src.sim.main_sim
   ```

   - usa parametri ragionevoli (es. 3 convogli, durata 120–180 minuti),
   - annota il percorso del CSV generato (`data/raw/...csv`).

2. (Opzionale) Usa `analyze_last_run.py` per vedere KPI rapidi della simulazione.

## 3. Costruzione dataset & (ri)training modello

1. Se previsto dal tuo flusso, ricostruisci il dataset:

   ```bash
   python -m src.ml.build_dataset
   ```

   (adatta al nome reale dello script usato per la costruzione del dataset).

2. Allena (o ri‑allena) il modello di rischio:

   ```bash
   python -m src.ml.train_risk_model
   ```

3. Verifica le metriche con il notebook o con gli script di valutazione (Fase 08).

## 4. Avvio API e UI

1. Avvia l'API in un terminale:

   ```bash
   uvicorn src.api.app:app --reload
   ```

2. Avvia la dashboard Streamlit in un secondo terminale:

   ```bash
   streamlit run src/ui/dashboard.py
   ```

3. Verifica `/health` e alcuni endpoint chiave (es. `/predict`) da Swagger.

## 5. Scenario demo per Planner + Analyst

1. Come Planner:
   - crea una missione demo (3–5 convogli),
   - esegui la simulazione,
   - usa la sezione di predizione rischio per valutare i convogli,
   - prova un suggerimento RL e prendi una decisione (conferma/override).

2. Come Analyst:
   - lancia `python -m src.ml.run_drift_check`,
   - controlla `python -m src.tools.api_latency_stats`,
   - valuta se i drift/SLO sono ok,
   - se vuoi, simula la necessità di un retraining e lancialo.

## 6. Chiusura demo

1. Ferma API e UI (Ctrl+C sui terminali).
2. (Opzionale) Esegui pulizia log/report troppo vecchi.
3. Prendi nota di eventuali problemi o miglioramenti da aggiungere al backlog.

```

3. Salva il file.

**Checklist**
- [ ] Esiste `docs/runbook_end_to_end_demo.md`
- [ ] Il documento descrive chiaramente una demo end‑to‑end eseguibile


---

### 2. (Opzionale) Creare `demo_all_in_one.bat`

> Questo passaggio è opzionale ma comodo: uno script per avviare rapidamente i pezzi principali.

1. Nella root del progetto, crea il file:

   - `demo_all_in_one.bat`

2. Inserisci un contenuto semplice, ad esempio:

```bat
@echo off
REM Demo rapida: attiva venv e mostra comandi principali (non automatizza tutto).

call .venv\Scripts\activate

echo.
echo === Digital Twin logistico - Demo rapida ===
echo.
echo 1) Esegui simulazione di esempio:
echo    python -m src.sim.main_sim
echo.
echo 2) Avvia API:
echo    uvicorn src.api.app:app --reload
echo.
echo 3) Avvia dashboard:
echo    streamlit run src/ui/dashboard.py
echo.
echo Per dettagli, vedi docs\\runbook_end_to_end_demo.md
echo.
pause
```

3. Salva il file.

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] Manuale Planner scritto
- [ ] Manuale Analyst scritto
- [ ] Runbook demo end‑to‑end creato
- [ ] (Opzionale) `demo_all_in_one.bat` creato e funzionante
