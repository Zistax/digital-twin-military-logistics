# Dataset e archivi delle simulazioni

Il dataset completo è conservato nel ramo dedicato
[`d03-dataset-v1`](https://github.com/Zistax/digital-twin-military-logistics/tree/d03-dataset-v1).
Il ramo `master` conserva codice, test, metadati e rapporti; la sua cronologia
non include i binari del dataset. Il ramo dati contiene una copia del codice
e i binari suddivisi in parti da massimo 4 MiB, verificabili e ricomponibili.
Non sono richiesti LFS o workflow GitHub Actions.

## Scaricare e ricomporre gli archivi

```bash
git clone --single-branch --branch d03-dataset-v1 https://github.com/Zistax/digital-twin-military-logistics.git digital-twin-dati
cd digital-twin-dati
python scripts/reassemble_dataset.py data/d03/payload --output ../archivi-d03
```

Lo script controlla SHA256 e dimensioni sia delle parti sia degli archivi
ricomposti. Non sovrascrive un archivio esistente con contenuto diverso.
Il clone del ramo dati e la ricomposizione richiedono alcuni GB di spazio;
l'estrazione delle tabelle complete richiede circa 30 GB aggiuntivi.
Per ottenere solo codice e rapporti usare `git clone --single-branch --branch master ...`.

## Contenuto

- I quattro `Dataset_D03_Parte_N_di_4.zip` contengono 90 run nativi v4,
  30 gruppi seed indivisibili, 8239 missioni e 1040241 snapshot rolling.
  Split: 54 training, 18 calibrazione, 18 test. Estrarli tutti nella stessa
  cartella e collocare `d03-batch-v1` e `d03-closeout-20261014` sotto `reports/`.
- `Simulazioni_Precedenti_e_Extra_v1.zip` conserva gli altri 134 JSONL,
  con percorsi relativi alla radice del repository: estrarlo dalla radice.
  Questi log storici non fanno parte dello split D03.
- La diagnostica dei due tentativi non accettati è in `master`, sotto
  `reports/d03-batch-v1/invalid-attempts-parts`; ricostruirla con
  `python scripts/restore_diagnostic_archive.py reports/d03-batch-v1/invalid-attempts-parts`.
- Cache, coverage locale e log storici aggiuntivi sono documentati in
  [snapshot diagnostico](../../reports/runtime-snapshot-20261014/README.md).

[Checksum dei quattro archivi D03](Verifica_Dataset_D03.json).
Il manifest nel ramo dati aggiunge i checksum delle singole parti e dell'archivio storico.

## Rigenerazione dal piano congelato

Seguire il [protocollo](../../docs/protocollo-d03-v1.md). Per rigenerare i run
in una nuova directory, copiare il solo `plan.json`, creare le sottocartelle
`records`, `bundles` e `traces`, poi dalla radice, con dipendenze installate
e PYTHONPATH che include il repository:

```bash
python scripts/produce_d03.py reports/d03-rigenerato --workers 3 --pressure-limit 3
```

La rigenerazione richiede diverse ore. I soli checkpoint versionati in `master`
non sostituiscono le tabelle: per usare il lotto già generato aggiungere i dati
del ramo dedicato.
