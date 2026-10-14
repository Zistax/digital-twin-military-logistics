# 10 — API & UI

## Endpoints
- `POST /simulate` → crea sessione (parametri, seed, n_missions); resp: `session_id`, path log, KPI prelim.
- `POST /predict` → rischio failure (pre‑partenza/rolling), soglie per priorità, SHAP on‑demand.
- `POST /optimize` → suggerimenti RL (azioni alto livello) in modalità **HITL**.
- `GET /runs | /sessions/{id} | /models` → stato, download, health.

## Contratti (estratto)
`/predict` Request: `schema_version, mode, priority, features{...}, explain_local`  
`/predict` Response: `p_failure, class_label, threshold_used, risk_band, top_features?, model_version, calibration_version, ts_utc, valid_until?`

## UI (FastAPI + React/Next.js)
- **Planner**: missioni, sim, mappa/rotta live, consigli RL (approva/rifiuta).
- **Analyst**: KPI, drift, calibrazione, soglie, champion/challenger.
- **Admin**: utenti/ruoli, segreti, storage, retention.
- **Viewer**: dashboard read‑only.

## i18n & Auth
- IT/EN (file di traduzione), SSO OIDC, RBAC.

## Diagramma — Architettura Azure
![Diagramma — Architettura Azure](img/azure_architecture.png)
