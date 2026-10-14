# Chiusura D03 — lotto iniziale e split

**D03 completato: 90 simulazioni verificate, 30 gruppi indivisibili.**
Il lotto contiene **8239 missioni** e **1040241 snapshot rolling**.
Siamo alla dodicesima voce su 18; la prossima è M01. Nessun modello addestrato o selezionato in D03.

| Insieme | Gruppi | Simulazioni | Per profilo | Missioni |
|---|---:|---:|---:|---:|
| training | 18 | 54 | 18 | 4949 |
| calibration | 6 | 18 | 6 | 1646 |
| test | 6 | 18 | 6 | 1644 |

## Distribuzioni descrittive

| Profilo | Missioni | Quote raggiunte | Censurate | Annullate | Puntuali | Ritardo noto | Classe ignota | Rolling |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| regular | 2057 | 1819 | 238 | 0 | 546 | 1511 | 0 | 190115 |
| pressure | 4125 | 2322 | 1803 | 0 | 581 | 3544 | 0 | 631248 |
| perturbed | 2057 | 1737 | 320 | 0 | 404 | 1653 | 0 | 218878 |
| all | 8239 | 5878 | 2361 | 0 | 1531 | 6708 | 0 | 1040241 |

Le categorie censura e ritardo noto possono sovrapporsi: oltre la scadenza il ritardo è noto anche quando la durata finale rimane ignota.

| Profilo | Urgente | Refrigerato | Missioni | Raggiunte | Censurate | Ritardo noto | Classe ignota |
|---|---|---|---:|---:|---:|---:|---:|
| perturbed | No | No | 1384 | 1111 | 273 | 1150 | 0 |
| perturbed | No | Sì | 286 | 240 | 46 | 256 | 0 |
| perturbed | Sì | No | 320 | 319 | 1 | 202 | 0 |
| perturbed | Sì | Sì | 67 | 67 | 0 | 45 | 0 |
| pressure | No | No | 2787 | 1284 | 1503 | 2522 | 0 |
| pressure | No | Sì | 548 | 259 | 289 | 514 | 0 |
| pressure | Sì | No | 642 | 635 | 7 | 403 | 0 |
| pressure | Sì | Sì | 148 | 144 | 4 | 105 | 0 |
| regular | No | No | 1384 | 1157 | 227 | 1068 | 0 |
| regular | No | Sì | 286 | 275 | 11 | 237 | 0 |
| regular | Sì | No | 320 | 320 | 0 | 170 | 0 |
| regular | Sì | Sì | 67 | 67 | 0 | 36 | 0 |

## Evidenza e limiti

Ogni bundle nativo v4 è stato esportato e riletto semanticamente; tutti e 90 sono stati riletti anche nell'audit finale. Verificati checksum, relazioni, conservazione, cutoff, contesti e maschere training. Nessun gruppo o identificativo attraversa gli insiemi.

Seed 1000–1029; esclusi i seed di sviluppo 0/1/2/3. Assegnazione congelata mediante hash prima del primo run. Generazione 7 giorni, estensione massima 7 giorni; nessuna sostituzione dei seed in funzione degli esiti.

Volumi ed esiti sono emergenti, senza riequilibrio artificiale. Snapshot e missioni dello stesso gruppo non sono osservazioni indipendenti. Le durate censurate rimangono nulle; i soli completati non rappresentano l'intera popolazione.

Il test è stato consultato soltanto per integrità e conteggi descrittivi. Non è stato usato per tuning, selezione di modelli, soglie o calibrazione. Nessuna misura di qualità predittiva è disponibile.

[Piano congelato](../d03-batch-v1/plan.json) · [Manifest degli insiemi](../d03-batch-v1/split_manifest.json) · [Audit finale](../d03-batch-v1/acceptance.json) · [Catalogo dei run](Catalogo_Run_D03.csv) · [Qualità](Qualita_D03.json)

[Protocollo](Protocollo_D03_v1.md) · [Esecuzione](Esecuzione_D03.md) · [Stato della roadmap](Stato_Roadmap.md)

La verifica di qualità dell'esecutore ha superato 268 test e 16 sotto-test, con copertura del nucleo del 91,78%; Ruff e Black superati. La prova è in `reports/d03-quality-executor/quality.json` nel repository.

Il limite di memoria ha richiesto una ripresa con rilascio dei risultati prima della rilettura; il simulatore congelato non è stato modificato. Un file troncato è stato ripristinato soltanto dopo aver riprodotto gli hash originali di tutte le otto tabelle e della traccia. I tentativi non accettati non entrano negli insiemi.

Modifiche locali, senza pubblicazione o invio a GitHub.
