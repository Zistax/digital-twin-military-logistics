# 07 — RL (azioni alto livello, reward, guardrail)

## Spazio azioni (alto livello)
- `go_to(waypoint)`
- `hold_k` con k∈{1,2,3}
- `reroute`
- `request_escort` (soglia rischio_eff ≥ 1.25, cooldown 5 step)

## Reward (γ = 0.7)
```
R = + 1.0 * (delivered_qty / required_capacity)
    + 0.5 * 1[mission_complete]
    − 0.01 * steps_norm
    − 0.7 * (#failures)
    − 1.0 * 1[timeout]
    − 0.02 * (#reroute) − 0.01 * (#hold_step)
```

## Curriculum
- Fase 1 (rischio/congestione bassi) → Fase 2 → Fase 3 (più difficili).

## Guardrail
- Risk budget medio ≤ **1.25**
- `max_reroute = 4`, `max_hold_total = 8`
- Cooldown `request_escort` = 5 step

## Training
- PPO (SB3), vec_env=8, total_timesteps=1e6
- Eval ogni 100k timesteps, early stop (patience 10)

## Baseline
- Shortest‑time, Safety‑first, Heuristica mista.

## Serving
- **Human‑in‑the‑loop** (fase 1) → **Automazione parziale** (fase 2).

## Diagramma — Azioni RL con guardrail e cooldown
![Diagramma — Azioni RL con guardrail e cooldown](img/rl_actions_guardrail.png)
