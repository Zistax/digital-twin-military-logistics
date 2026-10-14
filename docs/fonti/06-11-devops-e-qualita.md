# 11 — DevOps & Qualità

## Quality Gates
- Coverage **≥90%** (target futuro 95%), ruff/black, mypy stricter.

## Security
- `pip-audit`, `bandit`, **gitleaks**, container scan (Trivy), IaC scan (tfsec/Checkov).

## IaC (Azure)
- **Terraform** (VNet, Storage, Key Vault, Postgres, Private Endpoints).
- Ambienti: **dev → staging → prod** (approvazione manuale su prod).

## Monitoring & Load
- Azure **Application Insights** + **Log Analytics**; monitor SLO.
- Load test: **k6** (HTTP) + **Locust** (scenari).

## Release & Supply chain
- Artefatti **immutabili**, SBOM firmata, **provenance (SLSA‑lite)**.