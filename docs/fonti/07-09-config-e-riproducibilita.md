# 09 — Config & Riproducibilità

## Config composabile
```
conf/
  sim/{default.yml, dev.yml, prod.yml}
  data/{default.yml, ...}
  rl/{default.yml, curriculum.yml}
  api/{default.yml, prod.yml}
```
**Priorità**: CLI > ENV > YAML > default.

## Segreti & Cloud (Azure)
- **Key Vault** per segreti (prod); `.env` solo dev.
- Storage Blob (container: dvc‑remote, mlflow‑artifacts, parquet‑silver, parquet‑gold).
- **Private Endpoints** per Blob/KeyVault/DB (prod).

## Seeds & Determinismo
- `seed_sim`, `seed_ml`, `seed_rl` + `run_id`.
- Flags deterministici, log versioni.

## Dipendenze & Immagini
- **pip‑tools** (lock); immagini: `dtwin-dev`, `dtwin-train` (CPU), `dtwin-serve` (slim); variante GPU futura.

## Tracking & Dati
- **MLflow** (Docker Compose su VM), artefatti su Blob.
- **DVC** con remote Blob (dataset/versioning).

## CLI unificata
- `dtwin simulate | dataset build | train xgb | train ppo | eval rl | serve api | bake docker`

## Naming artefatti
- `models/{env}/xgb_convoy_vYYYYMMDD_sha.pkl`, `*_report.json`
- `rl/{env}/ppo_convoy_vYYYYMMDD_sha/…`

## CI/CD
- GitHub Actions: lint+tests, smoke dataset, build/push immagini, tag release (SemVer + Conventional Commits).