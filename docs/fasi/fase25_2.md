# Fase 25 – Checklist globale & Chiusura progetto (Parte 2, Giorni 4–6, Windows)

> **Obiettivo pratico (Parte 2)**  
> Chiudere il progetto in modo ordinato:
>
> - creare una **checklist globale** di qualità,
> - raccogliere un **backlog di prossimi passi**,
> - fare pulizia finale del repository e (se vuoi) taggare una prima release.

Questa parte è meno “coding” e più **governance del progetto**, ma è fondamentale
per poterlo riprendere tra 6 mesi senza perdersi.


---

## Struttura Fase 25 – Parte 2

- **Giorno 4** – Checklist globale (`docs/release_checklist.md`)
- **Giorno 5** – Backlog & next steps (`docs/backlog_next_steps.md`)
- **Giorno 6** – Pulizia repo & prima release/tag (facoltativo)


---

## Giorno 4 – Checklist globale di rilascio

### Obiettivo del giorno
- Riassumere in un unico documento tutte le verifiche importanti da fare
  prima di usare il sistema in una “demo importante” o in un ambiente più serio.


---

### 1. Creare `docs\release_checklist.md`

1. In VS Code, nella cartella `docs`, crea il file:

   - `release_checklist.md`

2. Inserisci una checklist strutturata, ad esempio:

```markdown
# Release Checklist – Digital Twin logistico

Questa checklist riassume i controlli da effettuare prima di una demo importante
o di un rilascio su un ambiente condiviso.

## 1. Codice & Qualita'

- [ ] `tasks.bat quality` eseguito con successo (lint + mypy + test con coverage)
- [ ] `pre-commit run --all-files` senza errori
- [ ] Coverage totale >= soglia concordata (es. 60–70% o piu')

## 2. Modello di rischio

- [ ] Ultimo training eseguito di recente (data non troppo vecchia)
- [ ] Metriche (AUC/Brier) soddisfacenti rispetto alle aspettative
- [ ] Soglie di rischio documentate (`docs/user_guide_analyst.md`)

## 3. Simulatore & RL

- [ ] Simulazione di esempio (`python -m src.sim.main_sim`) gira senza errori
- [ ] KPI base calcolabili (tempo medio, failure rate, ecc.)
- [ ] Env RL configurato e funzionante almeno in una configurazione base (se implementato)

## 4. API & Sicurezza

- [ ] `/health` risponde con `status = "ok"` o `degraded` accettabile
- [ ] Endpoint sensibili (`/predict`, `/simulate`, `/optimize`) protetti da API key
- [ ] API key configurata via `API_KEY_RISK` o file locale sicuro
- [ ] CORS configurato correttamente per la UI
- [ ] Tentativi di accesso falliti compaiono nei log audit (se testati)

## 5. Performance & SLO

- [ ] `python -m src.tools.api_latency_stats` eseguito di recente
- [ ] `python -m src.tools.check_slo` con esito positivo rispetto agli SLO definiti
- [ ] Latenze ragionevoli per gli endpoint principali (p95 entro target)

## 6. Drift & Retraining

- [ ] `python -m src.ml.run_drift_check` eseguito di recente
- [ ] Nessun PSI "rosso" o, se presente, documentato
- [ ] `python -m src.ml.retraining_decision` usato per valutare bisogno di retraining
- [ ] Eventuale retraining eseguito (`retrain_pipeline`) e documentato

## 7. Logging, Audit & Etica

- [ ] Log PII‑safe (sanitizzazione attiva, niente dati personali evidenti)
- [ ] `logs/audit/decisions.log` operational (se l'audit e' attivo)
- [ ] Note di sicurezza aggiornate (`docs/security_notes.md`)
- [ ] Terminologia neutra configurata in `conf/ops/terminology.yml`

## 8. Documentazione

- [ ] `README.md` aggiornato (comandi principali, struttura progetto)
- [ ] Guida Planner e Analyst aggiornate (`docs/user_guide_planner.md`, `docs/user_guide_analyst.md`)
- [ ] Runbook operativo (`docs/ops_runbook.md`) allineato allo stato attuale
- [ ] Runbook demo end‑to‑end (`docs/runbook_end_to_end_demo.md`) testato almeno una volta

## 9. Varie

- [ ] Script di retention (`python -m src.tools.retention_cleanup`) eseguito,
      o pianificato periodicamente
- [ ] Dipendenze aggiornate in modo ragionevole (no versioni troppo vecchie)
```

3. Salva il file.

**Checklist**
- [ ] Esiste `docs/release_checklist.md`
- [ ] La checklist copre qualità, modello, API, drift, etica e documentazione


---

## Giorno 5 – Backlog & prossimi passi

### Obiettivo del giorno
- Raccogliere in un solo posto tutte le idee **non ancora realizzate**,
  così da avere un “menu” chiaro per una futura Fase 2 del progetto.


---

### 1. Creare `docs\backlog_next_steps.md`

1. In VS Code, nella cartella `docs`, crea il file:

   - `backlog_next_steps.md`

2. Inserisci un contenuto simile (personalizzalo con le tue idee):

```markdown
# Backlog & Prossimi Passi – Digital Twin logistico

Questo documento elenca le principali attivita' che potrebbero essere sviluppate
in una fase successiva del progetto.

## 1. Modellazione & Dati

- [ ] Arricchire le feature con dati meteo/traffico piu' realistici
- [ ] Integrare dataset reali (dove possibile) con adeguata anonimizazione
- [ ] Migliorare la pipeline Gold con validazioni aggiuntive

## 2. Modello di rischio

- [ ] Introdurre SHAP o strumenti simili per spiegabilita' locale
- [ ] Aggiungere modelli challenger aggiuntivi (es. Random Forest, LightGBM)
- [ ] Esplorare calibrazione piu' avanzata delle probabilita'

## 3. RL & Ottimizzazione

- [ ] Implementare una policy RL completa (es. PPO) con curriculum
- [ ] Introdurre policy baseline aggiuntive per comparazione
- [ ] Migliorare la UI per il confronto Pareto (tempo vs rischio)

## 4. DevOps & Cloud

- [ ] Integrare MLflow per tracking di esperimenti
- [ ] Integrare DVC per versionare dataset
- [ ] Creare Terraform per ambienti Azure (dev/staging/prod)
- [ ] Pipeline CI/CD avanzata (build immagini, deploy automatico, scansioni sicurezza)

## 5. Sicurezza & Governance

- [ ] Integrare strumenti come `pip-audit`, `bandit`, `gitleaks`
- [ ] Migliorare il controllo accessi (ruoli: Planner, Analyst, Admin, Viewer)
- [ ] Introdurre gestione utenti/ruoli nella UI (RBAC)

## 6. UX & UI

- [ ] Portare la UI da Streamlit a front-end React/Next.js production-grade
- [ ] Introdurre i18n completo (IT/EN)
- [ ] Migliorare visualizzazioni su mappa, timeline missioni, heatmap rischi

## 7. Altre idee personali

- [ ] ...
```

3. Salva il file.

**Checklist**
- [ ] Esiste `docs/backlog_next_steps.md`
- [ ] Il backlog contiene sia idee dal design iniziale sia spunti personali


---

## Giorno 6 – Pulizia repo & (facoltativa) prima release/tag

### Obiettivo del giorno
- Sistemare il repository, eliminare file inutili,
- assicurarti che tutto sia committato,
- opzionalmente creare un tag `v1.0.0` o simile.


---

### 1. Pulizia file temporanei e cartelle inutili

1. Controlla che non ci siano file grossi o temporanei da committare per sbaglio:
   - output intermedi, file `.ipynb_checkpoints`, ecc.
2. Se necessario, aggiorna `.gitignore` per escludere file/cartelle che non vuoi tracciare,
   ad esempio:
   - `data/raw/`
   - `data/processed/`
   - `logs/`
   - eventuali `.env` locali.

3. Salva `.gitignore`.

**Checklist**
- [ ] `.git status` non mostra file temporanei o indesiderati da committare


---

### 2. Verifica finale qualità & demo

1. Esegui un giro completo di qualità:

```bash
tasks.bat quality
```

2. Esegui (almeno parzialmente) la demo end‑to‑end seguendo:

```text
docs/runbook_end_to_end_demo.md
```

3. Se trovi problemi, correggili e ripeti il giro.

**Checklist**
- [ ] `tasks.bat quality` passa
- [ ] La demo end‑to‑end gira senza errori bloccanti


---

### 3. (Facoltativo) Creare una prima release / tag Git

> Questo passaggio è facoltativo ma molto utile per “fotografare” lo stato del progetto.

1. Assicurati che tutti i file siano committati:

```bash
git status
```

2. Crea un commit finale di chiusura Fase 25 (se necessario):

```bash
git add docs/user_guide_planner.md docs/user_guide_analyst.md docs/runbook_end_to_end_demo.md docs/release_checklist.md docs/backlog_next_steps.md
git commit -m "Fase 25: demo finale, manuali e checklist globale"
```

3. Crea un tag (esempio `v1.0.0` – puoi scegliere tu il nome):

```bash
git tag v1.0.0
git push origin v1.0.0
```

4. Annota da qualche parte (es. in `README.md` o nel backlog) cosa contiene la versione taggata.

**Checklist (fine Giorno 6 – fine Fase 25 e fine roadmap)**
- [ ] Repo pulito e versionato
- [ ] Manuali e checklist scritti
- [ ] Demo end‑to‑end documentata
- [ ] (Opzionale) Primo tag/release creato
- [ ] Hai una visione chiara dei prossimi passi possibili


---

Con la Fase 25 chiudi la **roadmap iniziale** del progetto:

- hai codice, API, UI e strumenti operativi,
- hai una demo ripetibile,
- hai documentazione per ruoli diversi,
- hai una checklist per capire “quanto è pronto” il sistema
  e un backlog per decidere come investire il tempo nelle evoluzioni future.
