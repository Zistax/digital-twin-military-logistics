# Snapshot diagnostico locale — 14 ottobre 2026

Conservato su richiesta: cache Python/pytest/Ruff nell'archivio
`cache-temporanei.zip`, file `.coverage` alla radice e log storici
`data/audit/predict_calls.csv`, `data/raw/sim_events_20261007_114844.csv`.
Questi file documentano l'ambiente locale e non sono input del simulatore.
Le prove aggiornate di qualità rimangono nei rapporti D03.

I due tentativi non accettati sono conservati in
un archivio suddiviso in `reports/d03-batch-v1/invalid-attempts-parts`.
Ricostruirlo con:

```bash
python scripts/restore_diagnostic_archive.py reports/d03-batch-v1/invalid-attempts-parts
```

Il file troncato
originale è conservato nella cartella `storage-repairs`. Non usarli come
run validi: il manifest degli split identifica soltanto i 90 run accettati.
