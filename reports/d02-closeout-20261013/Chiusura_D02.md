# Chiusura D02 — pilota operativo e revisione dei parametri

13 ottobre 2026. **Undicesima voce completata per il nuovo nucleo operativo.**
Il controllo di accettazione del pilota è passato. Questo non chiude le lacune
F02/F03/D01 dell'intero progetto e non avvia il lotto D03 da 90 simulazioni.

Sono state eseguite nove simulazioni finali: tre seed di base (0, 1, 2), tre
profili per seed, sette giorni di generazione più fino a sette aggiuntivi.
Totale: 834 missioni, 598 quote raggiunte e 236 incomplete al cutoff.
Le 834 missioni non sono repliche indipendenti: i tre seed definiscono tre
gruppi di scenario, con varianti di profilo correlate.

## Risultati finali verificati

| Seed | Profilo | Missioni | Quote raggiunte | Incomplete | Puntuali | Tempo reale |
|---|---|---:|---:|---:|---:|---:|
| 0 | Regolare | 61 | 61 | 0 | 17 | 69.8 s |
| 0 | Sotto pressione | 139 | 84 | 55 | 18 | 242.4 s |
| 0 | Perturbato | 61 | 60 | 1 | 10 | 113.4 s |
| 1 | Regolare | 74 | 67 | 7 | 21 | 134.8 s |
| 1 | Sotto pressione | 145 | 77 | 68 | 24 | 277.9 s |
| 1 | Perturbato | 74 | 56 | 18 | 13 | 137.2 s |
| 2 | Regolare | 65 | 61 | 4 | 15 | 115.6 s |
| 2 | Sotto pressione | 150 | 76 | 74 | 19 | 274.2 s |
| 2 | Perturbato | 65 | 56 | 9 | 13 | 128.1 s |

Gli esiti incompleti mantengono durata finale nulla. Non vengono eliminati
allungando l'orizzonte e non viene imposto un bilanciamento 50/50.

## Criteri di uscita D02

| Controllo | Evidenza | Esito |
|---|---|---|
| Correttezza del nucleo | Nove run finali validi, invarianti controllate a ogni evento e pacchetti v3 riletti | Passato |
| Relazioni e conservazione | Verificati osservazioni/etichette, consegne, carichi e frazionamenti | Passato |
| Tracce operative | File con checksum e timestamp monotoni; scorte non negative e forniture future non esposte come effettive | Passato |
| Attese residue spiegate | Nessuna missione aperta priva di motivo operativo al cutoff in tutti i nove run | Passato |
| Varietà degli esiti | Quote puntuali, tardive e censurate osservate senza forzare le frequenze | Passato |
| Tempi praticabili del pilota | 69,8–277,9 secondi per run, entro budget tecnico del pilota di 600 secondi per run | Passato |
| Riproducibilità | Ripetizione del regolare del primo pilota con hash identico; tutti i sei file del seed 0 finale coincidono con il primo pilota nei tre profili | Passato |
| Revisione parametri | Decisioni e limiti documentati sotto, nessuna variazione fisica introdotta per migliorare artificialmente gli esiti | Completata |

Il limite di dieci minuti per run è un budget tecnico del pilota, non un SLO
approvato del prodotto, un vincolo operativo reale o un parametro generativo.
I tempi dipendono dall'ambiente e dalla concorrenza delle esecuzioni. La
sostenibilità delle code significa qui progresso verificato e censura spiegata:
il profilo sotto pressione non è in equilibrio e non esaurisce l'arretrato.
Non si conclude che una rete reale sarebbe adeguatamente dimensionata.

## Errore trovato e correzione verificata

Le prime prove sui seed 1 e 2 avevano rivelato `KeyError` nel reintegro urgente:
il motore tentava di sottrarre zero unità dalla riserva di una missione donatrice
che non conteneva l'articolo richiesto. La sottrazione ora avviene solo se ci
sono unità non protette da trasferire. Le regole di priorità e le quantità
restano quelle previste. Un test pubblico di flusso verifica che il recupero
attenda le scorte e poi consegni il deficit minimo senza alterare il donatore.

Gli esiti falliti sono conservati nei checkpoint preliminari
`pilot-d02-seed-1` e `pilot-d02-seed-2`, esclusi dal gruppo finale di accettazione.
Le nove esecuzioni ammesse sono state rifatte dopo la correzione nelle cartelle
`pilot-d02-final-0`, `pilot-d02-final-1` e `pilot-d02-final-2`.

## Revisione dei parametri: decisioni congelate

| Aspetto | Decisione | Motivo e limite |
|---|---|---|
| Domanda 10/20/10 al giorno | Mantenuta | Sotto pressione aumentano arretrato e censura nei tre seed; variabilità osservata |
| Orizzonte 7+7 | Mantenuto | Gli incompleti hanno causa operativa registrata e restano censurati |
| Scorte iniziali comuni | Mantenute | Confronto riproducibile senza conoscenza della domanda futura estratta |
| Banchine, calendari e priorità | Mantenuti | Caso controllato con due missioni concorrenti verifica che un fornitore finisca dopo la coda interna finita; diagnostica separa apertura, banchina e spazio |
| Scadenze senza stima finita | Budget convenzionale mantenuto e marcato | È parte esplicita di questo esperimento; la forte frequenza d'uso è un limite e gli esiti vanno segmentati per provenienza |
| Stimatore iniziale | Prima euristica mantenuta come baseline del pilota | La disponibilità futura dei mezzi e nuovi ordini non è prevista; non viene dichiarato calibrato o completo |
| Rollback dei comandi | Mantenuto | Una prova profilata breve mostra costo dominante nelle copie dello stato; nessuna rimozione dei controlli per accelerare il pilota |
| Seed 0, 1 e 2 | Riservati allo sviluppo | Usati per diagnosi e revisione: non diventano un test finale indipendente |

La durata finale media dei soli completati non è una stima dell'intera
popolazione censurata. I pesi rolling restano bilanciati per missione; i
campioni aggiuntivi non sono nuove missioni indipendenti.

## Evidenze conservate

`acceptance.json` contiene il controllo eseguibile passato, tutti i record,
le verifiche delle nove tracce, la coincidenza del seed 0 e gli hash dei sorgenti
al momento della chiusura. Gli hash non sostituiscono il completo manifesto
F03 del simulatore, del catalogo e delle feature.

Ogni cartella finale conserva i tre checkpoint, il riepilogo `pilot.json`,
le tracce orarie `trace-<seed>-<profilo>.jsonl` e tre pacchetti v3 completi.
Le tracce mostrano scorte, riserve, motivi delle code, banchine, forniture
osservate, allarmi e stati delle richieste/decisioni. Sono checkpoint orari,
non un registro completo di tutte le transizioni e non nuove feature Gold.
La chiusura di D02 non dichiara pertanto completa la voce D01.

La suite del nuovo nucleo passa **207 test**. Comprende competizione sulle
banchine, donatori privi dell'articolo, blocchi stock/flotta/guasto, checkpoint
senza futuro e controllo di accettazione del pilota. La suite storica API/ML
e la copertura globale del prodotto non sono state misurate.

## Passaggio successivo

L'undicesima voce è conclusa per il pilota operativo e la sua revisione.
Prima di D03 devono essere completati o formalmente circoscritti i requisiti
residui F02/F03/D01: manifesti completi, qualità storica, eventi e importazioni
rimanenti. Il controllo non dà automaticamente via libera a D03.

Il lotto futuro dovrà usare nuovi seed di base; tutte le varianti di ogni
seed devono restare nello stesso insieme train/calibration/test. Nessun test
finale è stato utilizzato per questa revisione. Nessun training, push o deploy.
