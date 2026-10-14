# D01 — osservazioni, esiti e KPI

13 ottobre 2026. Primo incremento, non ancora pipeline D01 completa.

Il runner acquisisce un record `creation-v1` prima della registrazione della
missione nel motore. Il record viene conservato nel risultato: non è ricostruito
dallo stato finale. Le osservazioni contengono identificativi, versione, tempo
simulato e timestamp UTC, attributi della richiesta, provenienza della scadenza,
prima stima, numero di mezzi liberi e righe con quantità, minimo, peso, volume,
refrigerazione, disponibilità all'origine e scorta a destinazione.

Questa prima selezione non include tutte le feature richieste dalla specifica:
restano da aggiungere contesto dettagliato di flotta, code, ambiente, forecast
e forniture, con contratti e controlli temporali propri.

`build_creation_dataset` valida whitelist, versione, campi temporali, quantità,
unità, riferimenti e duplicati. Un retry identico viene deduplicato; un record
conflittuale, orfano, un campo non autorizzato o un ritardo finale inventato
blocca la costruzione. La whitelist non può dimostrare la provenienza di dati
esterni falsamente inseriti in un campo ammesso: questo contratto è per i record
acquisiti dal runner, non un importatore generico di dati non fidati.

Gli esiti sono una tabella distinta, con cutoff finale, puntualità, ritardo,
istante della quota, censura, stato logistico ed eleggibilità. Gli annullamenti
sono esclusi dagli indicatori degli esiti eleggibili. Gli incompleti possono
avere ritardo già certo, ma non ricevono una durata finale fittizia.

I KPI riportano conteggi: missioni, annullamenti, quote raggiunte, censurate,
ritardi certi, esiti temporali sconosciuti e quote raggiunte puntualmente.
La media del ritardo riguarda soltanto le quote raggiunte, include gli zeri
puntuali ed è nulla quando non esistono osservazioni complete. Non è una stima
del ritardo medio dell'intera popolazione in presenza di censura.

## Esportazione riproducibile

`export_creation_dataset` crea una nuova cartella, rifiutando sovrascritture:

- `observations.jsonl`: feature alla creazione, senza etichette finali;
- `labels.jsonl`: esiti separati, da collegare tramite simulazione e missione;
- `manifest.json`: versioni, configurazione, gruppo del seed, KPI, conteggi
  e SHA-256 dei due file. Serializzazione UTF-8 con newline canonici.

Il gruppo `base-seed-N` mantiene insieme le varianti dello stesso seed. Non
assegna ancora train/calibration/test e non sostituisce il manifesto completo
di versione del simulatore richiesto da F03.

```bash
python -m src.logistics.experiments --seed 0 --days 1 --extension-days 1 --dataset-dir data/generated/creation-seed-0
```

## Verifica e prossimi passi

193 test del nuovo nucleo superati, inclusi sei test di dataset. Verificati
acquisizione prima delle consegne, censura, campi non autorizzati, cutoff,
deduplicazione, integrità dei collegamenti, esportazione e checksum ripetibili.

Restano: registro normalizzato di tutti gli eventi e movimenti, genealogia dei
lotti esportata, osservazioni rolling, importazione degli altri contratti e verifica dei manifesti, manifesti completi F03, dataset Gold con tutti i contratti temporali e KPI
segmentati. Il primo pilota esplorativo D02 è stato eseguito sul seed 0; D03 non è stato avviato.

## Importazione delle osservazioni alla creazione

`import_observations` riceve JSONL, contratti autorevoli delle missioni,
epoca UTC e cutoff. Restituisce record ammessi, righe in quarantena con numero,
contenuto originale e motivo, violazioni critiche e conteggi di qualità.
La quarantena è restituita al chiamante: il salvataggio di un report di
importazione e la CLI dedicata non sono ancora implementati.

Le righe malformate vengono escluse. L'importazione è bloccata oltre lo 0,5%
(esattamente 1 riga su 200 è ammessa); il confronto usa aritmetica intera.
Il denominatore è il numero di righe fisiche lette, comprese le ripetizioni.
Righe vuote interne contano come errori; il normale newline terminale no.

Una sola violazione critica blocca comunque l'intero risultato: campi feature
non autorizzati, cutoff incoerente o futuro, missione inesistente, avvio/scadenza
diversi dal contratto, UTC incompatibile con il tempo simulato, duplicati
conflittuali o più osservazioni di creazione per la stessa missione.
I retry identici vengono deduplicati. JSON con chiavi duplicate o costanti
non finite viene rifiutato. In caso di blocco `records` è vuoto; quarantena e
motivi restano disponibili e nessun subset viene presentato come dataset valido.

Sette test aggiuntivi verificano soglia esatta, superamento, errori critici
sotto soglia, incoerenza temporale anche su righe malformate, retry, conflitti
e forme JSON invalide. Questo importatore copre solo `creation-v1`: non
valida ancora file etichette esterni, eventi generici o checksum di bundle
ricevuti da altre fonti.

## Prime osservazioni rolling

Il runner acquisisce `rolling-v1` ogni ora, con intervallo configurabile tramite
`RunPolicy.observation_interval_s`. Avanza realmente il motore fino al campione:
non ricostruisce feature passate dallo snapshot finale. Alla stessa ora le nuove
richieste sono registrate dopo il campione; per esse vale la distinta osservazione
alla creazione. La frequenza di campionamento non cambia la granularità degli eventi.

I campioni includono stato operativo, tempo trascorso, tempo alla scadenza,
urgenza, quote minime, accettato, inutilizzabile ispezionato, riserve e stati
osservati delle richieste di recupero. Non includono danni nascosti, durate future
dei guasti o approvazioni future. Le missioni annullate o con quota già raggiunta
non producono ulteriori campioni. I record sono copie indipendenti dal motore.

Tre nuovi test verificano occultamento del danno prima dell'ispezione, campioni
vivi prima della consegna, arresto al raggiungimento della quota e annullamento.
I record sono per ora presenti in `rolling_observations` del risultato diagnostico:
non sono ancora validati/esportati dal bundle `creation-v1`. Restano da realizzare
contratto e importatore rolling, pesatura per missione, target di ritardo residuo,
campioni alla partenza e contesto completo di ambiente, flotta e code.

## Validazione ed esportazione rolling

`build_rolling_dataset` valida `rolling-v1` contro le osservazioni iniziali:
identità, versione, whitelist, articoli/minimi, tempi simulati/UTC, scadenze,
quantità osservate e cutoff finale. Blocca osservazioni successive alla quota,
righe conflittuali, articoli mancanti e feature non autorizzate. I duplicati
identici non aumentano il numero di campioni né alterano i pesi.

Il bundle esporta ora anche `rolling_observations.jsonl` e
`rolling_targets.jsonl`, entrambi con conteggi e checksum nel manifesto.
Prima della scadenza il target condizionale è il ritardo finale, soltanto per
missioni effettivamente tardive. Dalla scadenza in poi è il tempo residuo fino
alla quota. Target sconosciuti o non applicabili restano nulli, senza zeri
fittizi. Il target di classificazione `late` resta separato dalle feature.

Ogni campione eleggibile pesa 1/N, con N numero di campioni della missione;
gli annullamenti hanno peso zero. La somma dei pesi è uno per ogni missione
con campioni eleggibili. La ripartizione definitiva fra teste di classificazione
e regressione sarà definita nel training, applicando le rispettive maschere.

Quattro nuovi test coprono target prima/dopo scadenza, incompleti, pesi,
deduplicazione e rifiuto delle incoerenze. La suite completa passa 193 test.
Restano importazione esterna del contratto rolling con quarantena, verifica
dei bundle ricevuti, eventi completi, campioni alla partenza e feature contestuali.

## Verifica dei pacchetti ricevuti

`read_verified_bundle` verifica in sola lettura i quattro file JSONL e il
manifesto: nomi/versioni ammessi, file presenti, SHA-256, numero di righe,
JSON rigoroso, identità uniche, riferimenti fra tabelle, cutoff e pesi per
missione. I nomi sono fissi e i link simbolici ai file vengono rifiutati.
Un errore impedisce la restituzione di un pacchetto parzialmente valido.

Checksum ricalcolati non nascondono duplicati, riferimenti orfani o pesi
incoerenti. I checksum verificano però solo la corrispondenza al manifesto
fornito, non l'autenticità della fonte. Il verificatore non sostituisce la
validazione semantica completa delle etichette esterne né l'importazione
rolling con quarantena. Sei test nuovi coprono lettura, alterazioni, file
mancanti, orfani, pesi, duplicati e nomi di file non autorizzati.

## Coerenza delle etichette nei pacchetti

Il verificatore controlla ora anche il contratto delle etichette finali:
versione, tipi, stato, eleggibilità, censura, quota entro l'intervallo osservato,
puntualità e ritardo coerenti con la scadenza. Annullamenti e incompleti non
possono ricevere durate finali inventate. I target rolling devono concordare
con le etichette finali e con la fase precedente/successiva alla scadenza;
campioni posteriori al raggiungimento della quota vengono rifiutati.

Tre test aggiuntivi modificano etichette o target e ricalcolano i checksum:
i pacchetti vengono comunque respinti. Questo verifica coerenza interna,
non la veridicità degli eventi della fonte. Restano il contratto completo delle
feature rolling in importazione, quarantena degli altri formati, verifica
contro il registro eventi e normalizzazione degli eventi completi.

## Contratto rolling condiviso

Il validatore delle osservazioni rolling è ora condiviso fra costruzione interna
e lettura dei pacchetti. Anche un file con checksum aggiornato viene rifiutato
se contiene feature non ammesse, articoli mancanti, quantità negative, minimi
diversi dal contratto, timestamp o identità incoerenti. Un test aggiuntivo copre
quattro alterazioni delle feature. Suite: 193 test passati.

Il confronto delle quantità osservate con i totali finali è disponibile nella
costruzione interna; le etichette esportate non contengono quei totali. Per
verificare le quantità importate contro consegne realmente registrate resta
necessario esportare e validare il registro eventi. Restano inoltre quarantena
per import rolling isolato e normalizzazione completa degli eventi.

## Registro consegne e pacchetto v2

Il runner restituisce ora `delivery_events`, con contratto Delivery, identificativi
di missione/viaggio/batch/articolo, tempi fisici e osservati in secondi e UTC,
quantità accettate e inutilizzabili. L'export aggiunge `delivery_events.jsonl`.
Il manifesto passa alla versione 2: cinque file obbligatori; il lettore rifiuta
esplicitamente i vecchi pacchetti v1, da rigenerare, senza migrarli implicitamente.

Sia export sia lettura verificano eventi unici, riferimenti, articoli, cutoff e
UTC. Ricalcolano l'istante della quota dalle consegne osservate e lo confrontano
con l'etichetta finale. Ogni quantità accettata/inutilizzabile nei campioni rolling
è confrontata con gli eventi disponibili al suo cutoff: una consegna successiva
non può giustificare una feature precedente. Due nuovi test alterano una quantità
plausibile o rimuovono consegne, aggiornando i checksum, e verificano il blocco.

Questo è il registro delle consegne, non ancora il registro completo di tutti
gli eventi. Restano carichi/manifesti e genealogia per verificare la conservazione
per batch importato, movimenti di stock, guasti, decisioni e altre transizioni.
La coerenza del registro non dimostra l'autenticità di una fonte esterna.

## Manifesti fisici e genealogia: pacchetto v3

Il runner esporta `cargo_events`: carichi originari e frazionamenti con
missione, viaggio, batch, articolo, quantità e istante simulato. I carichi
originari vengono ricostruiti invertendo la genealogia dei frazionamenti,
senza contare i batch figli come nuovi approvvigionamenti.

Il bundle v3 richiede sei file, incluso `cargo_events.jsonl`. Export e lettura
riproducono cronologicamente carichi, split e consegne. Ogni split sottrae
quantità dal genitore e le assegna al figlio; ogni consegna sottrae dal batch
indicato. Vengono bloccati identità fisiche duplicate, riferimenti sconosciuti,
articoli diversi, split prima del carico e quantità superiori al disponibile.
I residui a fine replay possono essere positivi per missioni incomplete.

Quattro test aggiuntivi usano un recupero reale con due frazionamenti dello
stesso carico: il totale iniziale rimane dieci unità, senza crearne durante i
trasferimenti. Suite completa: 193 test. I pacchetti v1/v2 devono essere
rigenerati; non viene effettuata migrazione implicita.

Restano da normalizzare/esportare movimenti di magazzino, riserve, guasti,
richieste e decisioni. Il registro dei carichi verifica conservazione del
carico dichiarato, ma non ancora la sua provenienza dalle scorte iniziali e
dalle forniture. I timestamp UTC dei carichi e i manifesti di versione completi
restano da aggiungere al contratto persistente.

## Diagnostica delle attese per il pilota D02

Le forniture hanno ora contatori cumulativi per ordine e motivo: apertura,
banchina e spazio. Il conteggio parte dall'arrivo effettivo, esclude gli
intervalli di scarico attivo e termina con la chiusura. Quando più condizioni
bloccano contemporaneamente, viene registrato il primo controllo operativo:
apertura, poi banchina, poi spazio. Non è una stima causale della condizione
che da sola risolverebbe l'attesa.

Le missioni registrano anche il tempo dei motivi di mancata assegnazione
(stock, trasferimento a vuoto, piano euristico non fattibile o strada chiusa),
prima della partenza. Il registro non somma artificialmente questo tempo a
quello delle singole code, che può sovrapporsi: le due viste vanno analizzate
separatamente. Le attese delle richieste di recupero restano da dettagliare.

Questi contatori diagnostici non sono inseriti nelle feature ML. Quattro test
verificano inizio al vero arrivo, calendario, spazio pieno, banchina condivisa,
attesa stock prima dell'assegnazione e equivalenza degli avanzamenti spezzati.
La suite del nuovo nucleo passa 199 test. Non viene dichiarata chiusa D01.

## Chiusura del pilota D02

Il pilota operativo è stato completato su tre seed e nove run finali validi.
Le tracce orarie e le spiegazioni delle missioni ancora aperte sono conservate
nelle cartelle `reports/pilot-d02-final-*`; il controllo è in
`reports/d02-closeout-20261013/acceptance.json`. D01 rimane parziale nei punti
ancora elencati sopra: non è stata dichiarata chiusa insieme al pilota.
