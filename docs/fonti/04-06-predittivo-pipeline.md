# 06 — Predittivo (modelli, feature, soglie, API)

## Modelli & Tuning
- **Champion**: XGBoost binario (logloss).  
- **Challenger**: Logistic Regression.
- Tuning: **grid piccolo** (depth, lr, n_estimators).

## Feature
### Pre‑partenza
priorità, distanza/rotta (risk_base medio/max), #waypoints, capienza convoglio pianificata,
mix veicoli, **escort previsto**, stock origin/dest previsti, timeout per priorità,
congestione attesa, **meteo_forecast** (es. `precip_prob_mean`, `wind_speed_max`, `visibility_min`).

### Rolling
phase, pos, distance_to_dest, ETA, avg_speed, congestion_level, risk_dyn, load_total,
fail_count_so_far, tempo in fase, escort attivo.

## Calibrazione
- **Isotonic** se n ≥ 500, altrimenti **Platt**.

## Soglie operative (per priorità)
- Default: **High 0.60**, **Medium 0.70**, **Low 0.80** (editabili in UI).

## API `/predict`
**Request**: `schema_version, mode (predeparture|rolling), priority, features{{...}}, explain_local(bool)`  
**Response**: `p_failure, class_label, threshold_used, risk_band, top_features?, model_version, calibration_version, ts_utc, valid_until? (rolling)`

## Spiegabilità
- Global: importanze + **SHAP summary**.  
- Local (on‑demand): **SHAP top‑5**.

## Monitoring
- Qualità dati, drift (PSI), performance (AUC/Brier), champion/challenger (shadow).

## Sequence Diagram — /predict
![Sequence Diagram — /predict](img/sequence_predict.png)


## Workflow — Drift & Retraining
![Workflow — Drift & Retraining](img/workflow_retraining.png)
