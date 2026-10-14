# D02 — primo pilota e revisione dei parametri

13 ottobre 2026. Undicesima voce della roadmap di 18 voci.

Il primo pilota sul nuovo nucleo è stato eseguito: tre profili sullo stesso
seed di base 0, sette giorni di generazione e fino a sette giorni aggiuntivi.
Tutte le simulazioni hanno terminato senza violazioni delle invarianti e i
pacchetti v3 sono stati esportati e riletti dal validatore. Il caso regolare
è stato ripetuto con identico hash dell'intero risultato.

D02 è avviato concretamente, ma non ancora concluso: un solo seed di base
non misura la variabilità e le lacune F02/F03/D01 restano aperte. Il lotto D03
da 90 simulazioni non è autorizzato tecnicamente da queste sole prove.

## Esiti osservati

| Profilo | Missioni | Quote raggiunte | Incomplete al cutoff | Puntuali | Ritardi certi | Tempo reale | Arresto simulato |
|---|---:|---:|---:|---:|---:|---:|---|
| Regolare | 61 | 61 | 0 | 17 | 44 | 79.4 s | 10.958 giorni, missions_drained |
| Sotto pressione | 139 | 84 | 55 | 18 | 121 | 267.1 s | 14.000 giorni, time_limit |
| Perturbato | 61 | 60 | 1 | 10 | 51 | 119.6 s | 14.000 giorni, time_limit |

I ritardi certi includono le missioni incomplete con scadenza superata:
non sono tutti esiti conclusi. Gli incompleti mantengono durata finale nulla.
La media sui soli completati non stima il ritardo medio dell'intera popolazione.
I profili sono varianti correlate dello stesso seed; le 261 missioni non sono
261 repliche indipendenti. Non sono stati addestrati modelli.

## Code e qualità delle scadenze

| Profilo | Scadenze da stima | Scadenze da budget convenzionale | Picco missioni aperte campionato | Picco coda interna | Arretrato locale finale, unità |
|---|---:|---:|---:|---:|---:|
| Regolare | 13 | 48 | 38 | 10 | 2 |
| Sotto pressione | 16 | 123 | 102 | 10 | 471 |
| Perturbato | 10 | 51 | 45 | 10 | 386 |

Sotto pressione rimangono 55 missioni logisticamente aperte: 29 in attesa
con riserve insufficienti, 21 in attesa con riserve complete e cinque nello
stato `en_route` con un viaggio in attesa di scarico. Le 105 forniture in
attesa indicano una pressione sullo scarico; il registro disponibile non
basta a dimostrare se esista una priorità che penalizza sistematicamente i
fornitori. Questo va verificato con una traccia completa delle banchine.

La maggioranza delle scadenze deriva dal budget convenzionale di 24 ore,
moltiplicato per il margine estratto: 48/61 regolare, 123/139 sotto pressione,
51/61 perturbato. Il primo stimatore si astiene frequentemente perché non
prevede il rilascio della flotta occupata o nuovi approvvigionamenti. Le
frequenze di ritardo vanno segmentate per provenienza della scadenza prima
di usarle per scegliere parametri o modelli.

I picchi sono rilevati alle osservazioni orarie, non massimi continui.
I tempi di attesa esportati riguardano code di carico/scarico e sono sommati
fra i viaggi: non sono tempi medi per missione né misurano tutta l'attesa
per stock prima dell'assegnazione. Anche questa metrica va estesa.

## Revisione documentata

| Parametro o regola | Decisione dopo questo pilota | Motivo |
|---|---|---|
| Orizzonte 7+7 giorni | Mantenuto | Il limite produce censura esplicita e confrontabile; non viene allungato per eliminare gli incompleti |
| Frequenze 10/20/10 richieste al giorno | Mantenute | La pressione genera un carico e un arretrato maggiori; una sola base casuale non giustifica ricalibrazione |
| Scorte iniziali comuni ai profili | Mantenute | Conserva il confronto approvato; nessun aumento per nascondere carenze |
| Budget scadenza quando la stima manca | Mantenuto come convenzione, da riesaminare | Frequenza d'uso troppo elevata per considerare le scadenze pienamente basate sullo stato |
| Banchine, calendari e priorità di scarico | Nessuna modifica automatica | Serve analisi delle code e dei fornitori con eventi completi prima di variare capacità o priorità |
| Bilanciamento puntuali/tardivi | Nessuna imposizione | Gli esiti devono emergere dalle dinamiche |
| Prestazioni del motore | Da misurare su più seed e profilare | 79–267 secondi a run in questo ambiente; il caso sotto pressione costa circa 3,4 volte il regolare |

Nessun parametro fisico è stato cambiato in seguito a questo singolo pilota.
È una revisione con decisioni motivate e attività aperte, non una calibrazione.
La ripetizione regolare ha richiesto 85,9 secondi; i tempi dipendono dall'ambiente
e una parte delle esecuzioni si è sovrapposta alla prova di riproducibilità.
Non costituiscono un benchmark isolato.

## Cosa serve per chiudere D02

1. Completare le tracce D01: scorte/riserve, forniture, occupazione delle
   banchine, guasti, decisioni e transizioni; spiegare le attese residue.
2. Estendere la stima osservabile delle scadenze e confrontare i risultati
   con il budget convenzionale, senza consultare un futuro test finale.
3. Completare F02/F03: gate di qualità storici, manifesti di versione,
   configurazione e contratti persistenti. La copertura globale non è misurata.
4. Ripetere i tre profili su altri seed di base, confrontando censura,
   throughput, code, scadenze e costi di esecuzione.
5. Decidere e registrare eventuali modifiche, quindi rieseguire il pilota
   prima del lotto D03. Nessuna promozione automatica o tuning sugli esiti
   del futuro test finale.

## Evidenze e riproduzione

La suite del nuovo nucleo passa 195 test. Due nuovi test controllano input
invalidi del pilota e la diagnostica delle missioni completate/bloccate.
Il rapporto grezzo è `pilot.json`; i checkpoint sono `seed-0-*.json`.
Ogni cartella `seed-0-<profilo>` contiene il pacchetto v3 validato, con checksum.
`reproducibility.json` registra la ripetizione del regolare e la corrispondenza
dell'hash. Una prova ripetuta non è conteggiata come nuovo seed statistico.

```bash
python -m src.logistics.pilot reports/pilot-nuovo --seeds 0 --days 7 --extension-days 7
```

Il comando richiede una cartella nuova e salva un checkpoint per ciascun
profilo. Una simulazione non valida conserva tipo/messaggio dell'errore ed
è esclusa dai dati ammessi. Le modifiche e i risultati sono locali.
