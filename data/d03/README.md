# Dataset D03

Il lotto verificato comprende 90 simulazioni native v4, 30 gruppi indivisibili,
8239 missioni e 1040241 snapshot rolling. Split: 54 training, 18 calibrazione,
18 test. Il repository conserva piano, manifest, record, audit, rapporti e
script di generazione; non conserva gli oltre 28 GB di tabelle e tracce JSONL.

I dati già prodotti sono distribuiti nei quattro archivi elencati in
[Verifica_Dataset_D03.json](Verifica_Dataset_D03.json), con dimensioni, gruppi
e SHA256. Sono stati consegnati separatamente nella conversazione del progetto.
Gli archivi binari non sono stati caricati su GitHub: la connessione disponibile
consente modifiche Git, ma non il caricamento di asset di release o oggetti LFS.

Estrarre tutte le parti nella stessa cartella e collocare `d03-batch-v1` e
`d03-closeout-20261014` sotto `reports/`. I metadati comuni sono identici.
[Istruzioni complete](Leggimi_Dataset_D03.md).

## Rigenerazione dal piano congelato

Dalla radice, con le dipendenze installate e PYTHONPATH che include il repository:

```bash
python -m src.logistics.batch --help
```

Seguire il [protocollo congelato](../../docs/protocollo-d03-v1.md). Per riprodurre
le simulazioni in una nuova directory, copiare il solo `plan.json` dal lotto
versionato, creare `records`, `bundles` e `traces`, poi eseguire:

```bash
python scripts/produce_d03.py reports/d03-rigenerato --workers 3 --pressure-limit 3
```

Non riprendere direttamente la cartella dei soli metadati versionati: i checkpoint
indicano run accettati, ma senza gli archivi mancano i file nativi da rileggere.
La rigenerazione completa richiede spazio per circa 30 GB e diverse ore.
