# 08 — Metriche & Validazione

## Simulator (KPI)
- TtC, delivered_qty, failure_rate, eventi/100 km
- % tempo per fase (load/travel/unload/hold)
- congestione media/max, risk_eff medio/max, % timeout

## Analytics (modello)
- **AUC, PR‑AUC**, **Brier/ECE**, curve costo‑soglia per priorità
- Report JSON per ciclo + grafici (dashboard)

## RL (policy)
- Reward medio, TtC, % complete, failure_rate
- **Frontiera Pareto** vs baseline (tempo vs rischio vs delivered)

## Validazione
- Holdout per sessione + **k=5** stratificato
- Soglie **calibrate & cost‑aware** (pesi maggiori per High)
- Test significatività (bootstrap AUC/Brier; differenze tassi failure)

## Grafico — Frontiera Pareto (esempio)
![Pareto](img/pareto_policies.png)