# M01 — protocollo congelato prima dell'addestramento

Data: 15 ottobre 2026. Fonte: D03 v1, piano SHA256
`0b947c221014b117cf6bb2f3b3f1116d5aff59e74258fe1a9a3e60d8a663dcd0`.

## Perimetro e separazione

Solo osservazioni `creation-v1`: una riga per missione, al momento della richiesta.
Nessun target, identificativo, seed, profilo sperimentale o dato futuro entra nelle feature.
Le 54 simulazioni training sono divise in sei fold deterministici, ciascuno con
tre gruppi di seed; tutte le tre varianti di uno stesso seed restano insieme.
Le 18 simulazioni di calibrazione servono esclusivamente al fit sigmoidale finale
della probabilità selezionata. Nessuna tabella delle 18 simulazioni test viene letta.
Checksum degli archivi, delle tabelle e conteggi sono controllati prima del fit.

## Candidati e scelta

Classificazione: prevalenza training; baseline operativa (sigmoide dello slack
della stima osservabile e indicatore di stima mancante); regressione logistica
sulle feature complete; boosting ad alberi (80 iterazioni, profondità 3).
Selezione: minimo Brier sulle predizioni fuori fold training, ordine dei nomi
per pareggi esatti. AUC, PR-AUC, ECE in dieci intervalli fissi e numerosità
sono descrittive; nessuna ricerca successiva degli iperparametri.

Ritardo: confronto con `max(0, durata_operativa - tempo_concesso)`, mediana
training e boosting con perdita assoluta (80 iterazioni, profondità 3).
Si sceglie il minimo MAE fuori fold; mediana condizionata alle missioni che
raggiungono le quote in ritardo, non media della popolazione e non durata totale.
Annullate escluse; ritardi noti delle censurate inclusi nel classificatore;
censurate e puntuali escluse dalla regressione. Mai imputare una durata nulla.
La baseline operativa si astiene quando la stima non è disponibile: il suo MAE
va confrontato anche sul medesimo sottoinsieme, con copertura esplicita.
La selezione della durata avviene fra i candidati a copertura completa; la
baseline operativa con astensioni resta un confronto sul sottoinsieme comune.

## Supporto, calibrazione e limiti

La pipeline si astiene su schema non iniziale, valori invalidi o fuori dagli
intervalli training, depositi/categorie non osservati, segmenti con meno di
30 esempi o meno di tre gruppi. I segmenti sono urgenza × refrigerato ×
disponibilità della stima. La durata si astiene inoltre quando nel segmento
training oltre il 40% delle missioni è censurato o sono disponibili meno di
30 esiti tardivi completati in almeno tre gruppi. Soglie di supporto preventive,
non soglie di promozione M03. Le uscite identificano il target condizionato e
il tasso di censura; nessun intervallo o affidabilità reale è dichiarato.

Il modello selezionato è rifatto su tutto il training; una sigmoide a due
parametri, con regolarizzazione fissa C=1, è stimata sulla calibrazione.
Le metriche di selezione precedono questa calibrazione. Il fit di calibrazione
non è presentato come valutazione indipendente. Le metriche vengono riportate
per profilo, urgenza e refrigerato, con CI bootstrap al 95% su gruppi di seed
(400 ricampionamenti, seed 1401), avviso sotto 30 casi o tre gruppi.

## Chiusura

M01 richiede pipeline riutilizzabile, confronto reale riproducibile, astensione,
report e regressioni verdi. Non promuove un champion e non chiude M02/M03:
rolling, residuo, intervalli e test finale restano alle voci successive.
