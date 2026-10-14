# Digital Twin della Catena Logistica Militare — Progetto (Spec aggiornata)
Generato/aggiornato: 2025-11-07

## Scopo
Realizzare un **gemello digitale** della catena logistica militare che consenta di **simulare, prevedere e ottimizzare** in modo sicuro rifornimenti, trasporto e supporto operativo. Il progetto è pensato come **prodotto** (non solo MVP), con UI per utenti esterni, API, governance dei dati e stabilità operativa.

## Cosa include (endpoint-to-end)
- **Simulazione agent-based** su mappa **100×100 km** con waypoints, priorità, congestione, eventi di rischio (meteo, roadblock, comms), **code di deposito** con *preemption* e allocazione dinamica.
- **Predizione del rischio** pre-partenza e rolling con output calibrati e **spiegabilità locale/globale**; soglie per priorità.
- **Ottimizzazione** con policy **RL** ad azioni *alto livello* (go_to/hold/reroute/request_escort) e **guardrail** (risk budget, limiti d’azione, cooldown).
- **API & UI**: servizio API e dashboard per pianificare missioni, osservare KPI, drift e confrontare *champion/challenger* in **human‑in‑the‑loop**.
- **Data platform**: logging **events + trace** per sessione, **Parquet Silver/Gold**, validazione schema e quarantena; **drift** e **retraining on‑demand**.
- **Operatività & qualità**: config composabili, seeds separati, CI/CD, SLO (p95 inferenza < **600 ms**, uptime **99.5%**).

## Deliverable (contenuti o previsti)
- `docs/` — Design Spec per capitoli + **diagrammi** (stati simulatore, schema ER, Pareto, architettura Azure, sequence /predict, workflow retraining, code deposito, mappa waypoints, azioni RL).
- `data_contracts/` — JSON Schema per `events` e `trace` (con `schema_version`).
- `conf/` — configurazioni composabili (`sim/`, `data/`, `rl/`, `api/`) per `dev|staging|prod`.
- `src/` — simulatori/analytics/RL, pipeline feature (pre‑partenza/rolling) e validatori.
- `api/` — implementazione `/simulate`, `/predict`, `/optimize`, `/runs|/sessions|/models`.
- `ui/` — dashboard (planner/analyst/admin/viewer) con i18n e RBAC.
- `ops/` — IaC, CI/CD, osservabilità e sicurezza.
- `models/` — artefatti versionati (nomenclatura: `xgb_convoy_vYYYYMMDD_sha.pkl`, ecc.).

## Architettura di riferimento (sintesi)
- **App layer**: API per simulare, predire e proporre azioni; UI per pianificazione e monitoraggio.
- **Simulation layer**: agenti Convoy/Vehicle/Depot, waypoints, routing con costo (tempo + rischio + congestione), eventi e gestione code.
- **ML layer**: feature *Gold* per (sessione, convoglio); modello champion + challenger; **calibrazione**; soglie operative per priorità; spiegabilità on‑demand.
- **RL layer**: policy PPO con curriculum, baseline di confronto e **HITL** in produzione.
- **Data & MLOps**: Parquet Silver/Gold, validazione schema e quarantena, tracking esperimenti, versionamento dati e **trigger retraining** su drift (PSI/AUC/Brier).

## Scelte chiave (riassunto)
- **Logging**: `events` + `trace` per step convoglio; timestamp **UTC** + `t_step`; `schema_version` in ogni riga.
- **Unità ML**: (sessione, convoglio); dataset bilanciato iniziale ~50/50; split per sessione (holdout 20% + k=5).
- **Soglie** per priorità: High 0.60 · Medium 0.70 · Low 0.80 (editabili).
- **Guardrail RL**: risk budget ≤ 1.25; max_reroute=4; max_hold_total=8; cooldown escort=5 step.
- **SLO**: p95 inferenza < 600 ms; uptime 99.5%.
- **Governance**: audit decisioni HITL, reason codes, retention ≥ 365 gg, **circuit breaker** su drift/KPI.

## Come provare (flow di massima)
1. **Simula** una o più sessioni → generi `events.csv` e `trace.csv` + Parquet Silver.
2. **Build Gold** → aggregazione per (sessione, convoglio) con anti‑leakage e label finale.
3. **Allena** il modello → calibrazione, report metriche, registrazione artefatti e versioni.
4. **Serve** `/predict` → inferenza (pre‑partenza/rolling) + soglia per priorità + spiegazioni on‑demand.
5. **(Opz.)** RL `/optimize` → suggerimenti d’azione validati dall’operatore (HITL).
6. **Monitora** drift/performance → se trigger, **retraining on‑demand** e promozione champion/challenger.

## Note etiche & sicurezza
- Dati di esempio **interamente sintetici** (no PII), GDPR‑by‑design, audit completo.
- RBAC e *least‑privilege* per accessi; segreti in **gestione sicura**.
- Documentare assunzioni, limiti e ambito d’uso in ogni release.
