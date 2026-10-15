# Protocollo M02 v1 — 15 ottobre 2026

Congelato prima della lettura dei target rolling e dell'addestramento. Piano D03
immutato; commit di partenza `b35041bca8adea45e7909a740f4407da4e5155ce`.
Test finale riservato a M03: nessuna sua tabella viene estratta o analizzata.

## Snapshot e peso

Si leggono in streaming soltanto i 54 run training e 18 calibrazione accettati
dal catalogo. SHA256 degli archivi, manifest e tabelle verificati. Nessuna
ricostruzione retrospettiva: gli snapshot nativi hanno già il cutoff osservabile.
Per ciascuna missione e regime (prima/dalla scadenza) si conservano i quattro
snapshot con hash SHA256 minimo di `m02-v1|observation_id`, più il primo snapshot
di ciascuno stato operativo. Campionamento indipendente dai target.
Non si promette copertura simultanea di ogni istante non campionato.

Ogni missione ha peso totale uno, separatamente per regime e target incluso.
Anche metriche, fit, calibrazione sigmoidale e confronti usano tali pesi.
Validazione in sei fold per i medesimi gruppi indivisibili di seed di M01.
Preprocessing rifatto in ogni fold. Nessun profilo/seed/ID diventa una feature.

## Target, candidati, scelta

Prima della scadenza: probabilità di ritardo e mediana del ritardo condizionata
a esito tardivo completato. Dalla scadenza: tempo residuo condizionato a quota
raggiunta nel periodo osservato; probabilità omessa. Ritardo finale e intervallo
finale sono accumulato più residuo e relativo intervallo. Nessuna durata delle
censurate viene imputata; classificazione delle censurate con ritardo noto ammessa.

Classificazione: prevalenza, logistica C=1 con solver liblinear e massimo 2000
iterazioni, boosting 80 iterazioni/profondità 3 con i parametri fissi M01.
La scalatura usa media/varianza ponderate a due passaggi, con colonne costanti
a scala unitaria per evitare cancellazione numerica. Scelta con minimo Brier
ponderato fuori fold training.
Durata, separatamente prima e dalla scadenza: mediana ponderata e boosting
con perdita assoluta, 80 iterazioni/profondità 3; minimo MAE ponderato fuori fold.
Pareggi risolti in ordine alfabetico. Baseline operativa M01 come riferimento
iniziale, senza assimilarla a stima aggiornata della flotta.

## Calibrazione e intervalli

Sigmoide C=1, fit sulle sole osservazioni pre-scadenza di calibrazione,
pesi per missione. Non si presenta il suo fit come performance indipendente.

Intervalli simmetrici non negativi, obiettivo nominale 80%, separati per
previsione iniziale, ritardo rolling pre-scadenza e residuo post-scadenza.
Il punteggio è il massimo errore assoluto fra gli snapshot ammessi di una
missione, poi il massimo fra le missioni e le tre varianti di un gruppo di seed.
Quantile di rango `ceil((G+1)*0.8)` dei G punteggi di calibrazione; se il rango
non è disponibile si omette l'intervallo. Con sei gruppi il rango è sei:
intervalli prevedibilmente larghi e copertura obiettivo non garantita su dati reali.
Scoring solo sui completati tardivi: intervalli esplicitamente condizionati,
non soluzione del problema di sopravvivenza/censura.

Per una verifica interna onesta della calibrazione, si assegnano i 18 gruppi
training in tre blocchi disgiunti da sei: a rotazione sei gruppi per fit,
sei per calibrazione e sei per verifica. Si valutano copertura e ampiezza su
gruppi mai usati per fit/calibrazione di quel ciclo. È diagnostica interna
training con ricetta boosting fissata qui (anche se la selezione finale scegliesse
un'altra famiglia); il test finale resta intatto. Nessuna scelta dei candidati su tale
diagnostica, nessuna modifica di soglie dopo averne letto i risultati.

## Supporto, spiegazione e tracciabilità

Guardie M01: 30 missioni in tre gruppi; durata con almeno 30 esiti completati
tardivi in tre gruppi e censura non oltre 40%. Segmento rolling:
regime × urgenza × refrigerato × disponibilità della stima iniziale.
Valori fuori dal dominio numerico/categorie training o contratto incoerente
causano astensione. Target fuori supporto non riceve una durata o un intervallo.
Le feature distinguono stato corrente (avanzamento, deficit, riserve, recuperi
già osservati) dalle condizioni iniziali congelate. Nessun futuro guasto/meteo.
Spiegazioni descrittive di stato e deficit, non causali.

Gli snapshot D03 sono orari: non vengono riscritti retrospettivamente. Un servizio
separato controlla il simulatore vivo a ogni passo pubblico, agli eventi osservati,
ogni 1800 secondi configurabili e all'istante esatto della scadenza. Le chiamate
successive nello stesso istante aggiornano lo stesso record, dopo il batch osservabile.
Arresto a quote raggiunte/annullamento e controllo alla scadenza sono verificati
con il simulatore reale in test dedicati. Le metriche statistiche restano sugli
snapshot D03 campionati: non dimostrano copertura di tutti gli istanti della
nuova frequenza di aggiornamento. Ogni predizione esportata
include snapshot, cutoff, versione, hash del modello e motivi di astensione;
la UI/API resta U01. P14 chiuso per questo perimetro, P15/promozione resta M03.
