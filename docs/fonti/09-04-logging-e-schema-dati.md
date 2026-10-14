# 04 — Logging & Schema Dati

## Struttura per sessione
- CSV: `session_{id}_events.csv` e `session_{id}_trace.csv`.
- Parquet: **Silver** (raw pulito) e **Gold** (feature ML) partizionati.

## Identificatori
- `session_id` obbligatorio; chiave `(session_id, convoy_id)`; `mission_id` opzionale.

## Eventi — Campi
- **Obbligatori**: `ts_utc, t_step, event, session_id, convoy_id, priority, x, y, waypoint_id/edge_id, risk_base, risk_dyn, risk_eff, qty, depot_id, depot_stock, phase, schema_version`
- **Opzionali**: `vehicle_id, details(json), congestion_level, escort_present, timeout_remaining, parked_flag, recovery_flag`

## Trace Convoglio — Campi (1 riga/step/convoglio)
`ts_utc, t_step, session_id, convoy_id, phase, x, y, speed, eta_min, distance_to_dest_km, risk_eff, num_vehicles, load_total, escort_present`

## Enumerazioni
- priorità: `low|medium|high`
- eventi: `load|unload|attack|breakdown|repaired|mission_complete|mission_timeout|reroute|regroup|hold|weather_delay|roadblock|comms_loss|supply_disruption|parked`
- fasi: `idle|load|travel|unload|hold|reroute|regroup|complete|parked`

## Versioning & Validazione
- `schema_version` in ogni riga.
- **JSON Schema** in `data_contracts/`; validatore in ingest.
- **Quarantena** righe invalide; **hard‑fail** se >0.5%.

## Timestamp
- Sempre **UTC** (+ `t_step`). Local time calcolato in UI.

## Diagramma — ER schema logs/trace/gold
![ER schema](img/er_logs.png)