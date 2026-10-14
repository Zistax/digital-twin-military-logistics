# Esecuzione D03 e ripresa dai checkpoint

Il protocollo scientifico rimane `protocollo-d03-v1.md` e il piano congelato è
`reports/d03-batch-v1/plan.json`. Seed, profili, orizzonti, gruppi, split e
sorgenti del simulatore non sono cambiati durante la produzione.

La prima esecuzione a sei processi ha superato il limite di memoria di 8 GiB.
Gli otto checkpoint già verificati sono stati conservati. Una ripresa a due
processi ha portato il totale a dieci checkpoint validi.

Il picco includeva contemporaneamente il risultato completo della simulazione
e la rilettura indipendente delle stesse tabelle. L'esecutore in
`scripts/produce_d03.py` libera il risultato prima della rilettura e limita
separatamente i profili sotto pressione. Il codice del simulatore rimane quello
registrato nel piano. L'hash dell'esecutore e i limiti operativi sono in
`memory-executor.json`.

Due regressioni verificano il rilascio del risultato, l'equivalenza degli export
e il limite sui run sotto pressione. È stata verificata anche l'equivalenza
byte per byte di tutte le otto tabelle e del manifest della simulazione nativa
`scenario-1025-regular`, fra il primo tentativo e quello accettato con il nuovo
esecutore. La prova è in `memory-executor-native-equivalence.json`.

Le interruzioni successive della sessione sono registrate separatamente. I
checkpoint completi rimangono validi; i tentativi con file ma senza checkpoint
sono conservati come non accettati. Non si sostituiscono i seed e non si
importano risultati parziali negli insiemi.

Comando operativo dalla radice, con `PYTHONPATH` che include il repository:

```bash
python scripts/produce_d03.py reports/d03-batch-v1 --workers 3 --pressure-limit 3
```

Usare un solo coordinatore sulla directory. Prima di una ripresa verificare
che l'esecutore precedente sia terminato. Il programma salta i checkpoint
validi e rivalida tutti i 90 bundle nell'audit conclusivo. La voce D03 non è
chiusa finché `acceptance.json` non riporta `passed: true` e 90 run verificati.

Il file `progress.json` contiene il conteggio corrente, mentre `records/`
conserva l'esito di ogni tentativo. Le durate reali e il parallelismo sono
metadati di esecuzione, esclusi dai target e dalle feature del simulatore.

## Ripristino di un file troncato

L'audit dei byte del 14 ottobre ha rilevato un solo file troncato fra i 49
checkpoint controllati: `operational_events.jsonl` di
`scenario-1004-perturbed-attempt-1`. La causa non è stata determinata.

La rigenerazione deterministica ha riprodotto gli hash originali di tutte le
otto tabelle, della traccia e i metadati del run. È stato sostituito soltanto
il file danneggiato, conservandone una copia diagnostica. Manifest, checksum,
seed e piano sono rimasti invariati. L'evidenza è in
`reports/d03-batch-v1/storage-repairs/scenario-1004-perturbed/restoration.json`.
L'audit nativo conclusivo deve comunque verificare nuovamente ogni bundle.

## Ultima tranche di soli profili sotto pressione

Dopo 79 checkpoint validi rimanevano soltanto 11 profili sotto pressione.
La memoria anonima osservata con due run attivi era 1,49 GiB su un limite
di 8 GiB, senza OOM nella sessione. Il coordinatore è stato fermato e ripreso
con tre processi totali e tre slot sotto pressione. La politica precedente
è conservata in `memory-executor-initial-policy.json`; il passaggio è
registrato in `execution-resource-transition-3.json`. Nessuna modifica al
codice dell'esecutore, al simulatore o al piano scientifico.

Per ridurre lo spazio occupato, i due tentativi non accettati della prima
esecuzione sono conservati in `invalid-attempts-preserved.zip`: tutti i 18
file sono stati riletti e confrontati con SHA256 prima di eliminare le copie
non compresse. Manifest e record rimangono nelle posizioni originali;
`invalid-attempts-archive.json` documenta gli hash e i record indicano
l'archivio e il prefisso da estrarre. Nessun bundle accettato è stato rimosso.
