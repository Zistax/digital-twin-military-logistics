# 01 — Visione & SLO

## Scopo
Prodotto decisionale per logistica convogli con **simulatore ABM**, **predizione rischio** e **policy RL**, esposto via **API + UI** ad **utenti esterni**.

## Utenti & Ruoli (RBAC)
- **Planner**: crea missioni, lancia simulazioni, approva suggerimenti RL.
- **Analyst**: controlla KPI, drift, calibrazione, imposta soglie/alert.
- **Admin**: utenti/ruoli, segreti/connessioni, retention, ambienti.
- **Viewer**: sola lettura (dashboard, report).

## Obiettivi & Ambito
- **Analisi decisionale** (pre‑partenza e rolling).
- **Dati reali + pubblici** con governance.
- **UI** production‑grade (FastAPI + React/Next.js, i18n IT/EN).
- **Stabilità** e qualità (SLO & CI/CD).

## SLO & SLA
- **Uptime**: 99.5% mensile.
- **Inferenza /predict**: p95 < **600 ms** (p99 < 1 s).
- **Simulazioni**: job **asincroni**; “inizio entro 1 min” (coda).
- **Storage**: retention configurabile per tenant (preset 90/180/365/custom; default 180 dati sim, 365 audit).

## Modalità operative
- **Predizioni**: realtime + batch giornaliero.
- **RL**: Fase 1 **Human‑in‑the‑loop**, Fase 2 **Automazione parziale** con guardrail.
- **Lingue UI**: IT + EN (i18n).

## Metriche di Successo (estratto)
- Accuratezza calibrata (AUC/PR + **Brier/ECE**).
- Riduzione failure rate e/o TtC vs baseline, frontiera **Pareto** (tempo vs rischio).
- Latenza rispettata, drift monitorato e retraining on‑demand.