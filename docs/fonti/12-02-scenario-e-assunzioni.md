# 02 — Scenario operativo & Assunzioni

## Spazio & Tempo
- **Mappa**: 100×100 km (1 unità = 1 km).
- **Step temporale**: 5 minuti.

## Missioni & Concorrenza
- Missioni concorrenti abilitate; limiti per ruolo:
  - Planner: max 5 attive; Admin: max 50; limite sistema: 100/sessione.

## Rischio & Dinamiche
- **Rischio effettivo** = `risk_base` (per rotta) × `m_dyn` (dinamico in [0.8, 1.5], durata spike 6–12 step).
- **Eventi**: attack, breakdown; condizioni esogene (meteo, roadblock, comms, supply).

## Veicoli & Convogli
- Tipi: **truck/armored/jeep** (capacità/velocità/robustezza diverse).
- Convoglio: dimensione variabile; **escort** attivabile su rischio alto.

## Priorità & Timeout
- Priorità: high/medium/low influenzano percorso, velocità e allocazione mezzi.
- Timeout missione: High 2h (24 step); Medium 4h (48); Low 6h (72).

## Carico/Scarico & Depositi
- Base: 20 u/step × **banchine=2**; moltiplicatori per veicolo (truck 1.2×, armored 0.8×, jeep 0.6×).
- Replenishment: +200/ora; **urgent +300** con lead 30 min (High in coda & stock<30%).