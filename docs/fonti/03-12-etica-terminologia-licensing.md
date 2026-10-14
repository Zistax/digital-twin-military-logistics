# 12 — Etica, Terminologia & Licensing

## GDPR & Privacy
- Data minimization, EU residency, pseudonimizzazione ID, **no PII** nei log.
- **DPIA** e **DPA** con fornitori quando necessario.

## Terminologia (multi‑tenant)
- UI **neutra e configurabile**: `attack → threat_event`, `breakdown → mech_failure` (mapping per tenant).

## Governance del Modello
- Log decisioni operatore vs suggerimenti RL; reason codes (top‑features), versioni modello.
- Retention 365+ per audit; **circuit breaker** se drift forte/KPI sotto soglia.

## Licenza
- **Dual license**: core **Apache‑2.0**, plugin/connettori **proprietari**.