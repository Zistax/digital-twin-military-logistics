# 03 — Simulatore (dinamiche & agenti) — Processi

## Agenti & Spazio
- Agenti: **Depot**, **Vehicle** (tipi), **Convoy**.
- Spazio: **waypoints** + archi (distanza, risk_base, capienza, speed_limit).

## Macchina a stati Convoy
`idle → load → travel → (reroute|regroup|hold) → unload → complete`
- Trigger **reroute**: spike `m_dyn > 1.25` o `roadblock` su arco.
- Trigger **regroup**: `vehicle_gap > 2 km` o `> 2 step`.
- **Timeout**: logica Park & Resume (safe‑point; nuova missione).

## Processi principali
### P1 — Pianificazione rotta
**Input**: origine/dest, priorità, grafo, rischio, congestione attesa.  
**Step**: calcolo costo `tempo + λ_risk*risk_eff + λ_cong*cong`; scelta percorso.  
**Output**: lista waypoints, ETA, rischio previsto.

### P2 — Movimento
**Input**: prossimo arco, speed base × (meteo, congestione, escort).  
**Step**: avanzamento, safety gap, eventuale rallentamento.  
**Output**: nuova pos, `distance_to_dest`, `phase=travel`.

### P3 — Gestione rischio
**Input**: `risk_eff` su arco, condizioni esogene (meteo/roadblock/comms).  
**Step**: se soglia superata ⇒ `reroute`; se comms_loss ⇒ no reroute per 3–6 step.  
**Output**: rotta aggiornata o proseguimento.

### P4 — Carico/Scarico & Code deposito
**Input**: banchine disponibili, priorità, veicoli presenti.  
**Step**: FCFS con **preemption** (max 1 sorpasso/60 min), allocazione dinamica se ETA≤2 step.  
**Output**: `load/unload` event, update stock, `delivered_qty`.

### P5 — Breakdown & Repair
**Input**: failure, priorità, ETA riparazione.  
**Step**: High: leave‑behind se repair>2 step; Med/Low: wait fino 6 step poi leave. Recovery mission.  
**Output**: `repaired` o veicolo lasciato, update capacità.

### P6 — Park & Resume (Timeout)
**Input**: timeout per priorità.  
**Step**: parcheggio su safe‑point, log `parked`; schedula follow‑up in 60–120 min.  
**Output**: `mission_timeout` + `park_cost`; nuova missione.

## KPI simulatore
TtC, delivered_qty, failure_rate, eventi/100 km, %tempo per fase, congestione media/max, risk_eff medio/max, %timeout.

## Diagramma — Macchina a stati
![State machine](img/sim_state_machine.png)

## Diagramma — Code deposito (FCFS + preemption + allocazione dinamica)
![Diagramma — Code deposito (FCFS + preemption + allocazione dinamica)](img/deposit_queue.png)


## Mappa — Waypoints d'esempio (100×100 km)
![Mappa — Waypoints d'esempio (100×100 km)](img/waypoints_map.png)
