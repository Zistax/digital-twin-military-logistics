# 05 — Strategia Dataset

## Unità & Bilanciamento
- Unità di training: **(session_id, convoy_id)**.
- Bilanciamento iniziale: ~**50/50** (mix safe/risk).

## Volume & Split
- Target: **500** campioni/ciclo (range 300–1000).
- Split: **holdout 20% per sessione** + **k=5** fold (per report).

## Variabilità sintetica (sampling)
- `attack_prob ~ Beta(2,20)` → [0, 0.05]
- `breakdown_prob ~ Beta(2,15)` → [0, 0.04]
- `m_dyn ~ Uniform(0.8, 1.5)` durata 6–12 step.

## Label & Anti‑Leakage
- Target **binario** `failure` + **severity** separata (analisi).
- Cutoff temporale **t_pred** (pre‑partenza, rolling) + validatore automatico.

## Gold ML (Parquet)
- Feature (sessione, convoglio): `fail_count, load_ops, unload_ops, delivered_qty, ttc_min, avg_speed, max_risk, avg_congestion, had_escort, stock_origin, stock_dest`.

## Drift & Retraining
- Trigger retraining se: **PSI > 0.2** o **AUC −5pp** o **Brier +0.02**.
- Ground truth a fine missione; ETL 60 min; backfill fino 24h.