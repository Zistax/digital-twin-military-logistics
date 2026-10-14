# Dataset e log completi

I file binari sono suddivisi in parti da massimo 4 MiB per consentire il
trasferimento attraverso le API Git. Ogni parte e ogni archivio completo
hanno checksum SHA256. `manifest.json` elenca tutti i file e le dimensioni.

Dalla radice del clone di questo ramo:

```bash
python scripts/reassemble_dataset.py data/d03/payload --output ../archivi-d03
```

Si ottengono i quattro ZIP del lotto D03 e l'archivio dei 134 JSONL storici
e supplementari. Leggere `data/d03/README.md` per le istruzioni di estrazione.
Nessun workflow o codice viene eseguito automaticamente da questo ramo.
