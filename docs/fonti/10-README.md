# Digital Twin Logistics — Documentazione (v1.0, 2025-11-07)

Questa cartella contiene un file **per ogni parte** del progetto, con **dettagli di processo** (input → step → output, ruoli, metriche, SLO, decision gate).  
Le specifiche riflettono le decisioni condivise nella fase di design.

## Indice
1. [01 — Visione & SLO](01-visione-e-slo.md)
2. [02 — Scenario operativo & Assunzioni](02-scenario-e-assunzioni.md)
3. [03 — Simulatore (dinamiche & agenti)](03-simulatore-processi.md)
4. [04 — Logging & Schema dati](04-logging-e-schema-dati.md)
5. [05 — Strategia Dataset](05-strategia-dataset.md)
6. [06 — Predittivo (modelli, feature, soglie, API)](06-predittivo-pipeline.md)
7. [07 — RL (azioni alto livello, reward, guardrail)](07-rl-policy.md)
8. [08 — Metriche & Validazione](08-metriche-e-validazione.md)
9. [09 — Config & Riproducibilità](09-config-e-riproducibilita.md)
10. [10 — API & UI](10-api-e-ui.md)
11. [11 — DevOps & Qualità](11-devops-e-qualita.md)
12. [12 — Etica, Terminologia & Licensing](12-etica-terminologia-licensing.md)

> Suggerimento: usa questo indice come guida di lettura; ogni file è auto‑contenuto e indipendente.


## Diagrammi
- Macchina a stati (simulatore): [PNG](img/sim_state_machine.png) · [SVG](img/sim_state_machine.svg)
- ER schema (dati): [PNG](img/er_logs.png) · [SVG](img/er_logs.svg)
- Frontiera Pareto (esempio): [PNG](img/pareto_policies.png) · [SVG](img/pareto_policies.svg)

- Architettura Azure: [PNG](img/azure_architecture.png) · [SVG](img/azure_architecture.svg)
- Sequence /predict: [PNG](img/sequence_predict.png) · [SVG](img/sequence_predict.svg)
- Workflow retraining: [PNG](img/workflow_retraining.png) · [SVG](img/workflow_retraining.svg)

- Code deposito: [PNG](img/deposit_queue.png) · [SVG](img/deposit_queue.svg)
- Waypoints esempio: [PNG](img/waypoints_map.png) · [SVG](img/waypoints_map.svg)
- Azioni RL + guardrail: [PNG](img/rl_actions_guardrail.png) · [SVG](img/rl_actions_guardrail.svg)
