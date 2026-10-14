# Primo nucleo missioni — contratti e verifica

Implementazione dell'8 ottobre 2026, riferimento: Specifica unificata v1,
sezioni 3, 15, 21–23. Modulo: `src/logistics`.

## Perimetro consegnato

Contratti Python validati per missione, righe articolo e consegne ispezionate;
replay deterministico di una missione con manifesti di carico espliciti.
Non è ancora un simulatore completo: il caso di riferimento fornisce eventi
prefissati, non genera automaticamente carichi, percorsi o tempi di viaggio.
Il prototipo storico resta separato; API e modello ML non usano ancora il nuovo modulo.

## Contratti eseguibili

| Entità | Campi e vincoli |
|---|---|
| Mission | simulation_id, mission_id, origin_id, destination_id non vuoti; origine diversa da destinazione; start_s >= 0; deadline_s > start_s; tuple non vuota di righe con articoli unici |
| MissionLine | item_id; requested intero positivo; threshold Decimal finito in (0,1]; minimum = ceil(requested × threshold) |
| Manifesto | mappa (trip_id, batch_id, item_id) → unità intere positive; batch univoco nel manifesto; articolo presente in missione |
| Delivery | event_id, simulation_id, mission_id, trip_id, batch_id, item_id; occurred_s e observed_s interi non negativi, observed_s >= occurred_s; accepted e unusable non negativi, somma positiva; schema_version = 1 |
| Outcome | stato obiettivo; quota_reached_s; late nullable; delay_minutes nullable; accettato, inutilizzabile e residuo a bordo per articolo; istante quota per articolo; logistics_complete |

Gli identificativi sono forniti dal chiamante e stabili durante il replay.
Le unità sono indivisibili; booleani e float non sono quantità intere valide.
Il manifesto contiene merce già caricata: non rappresenta scorte di deposito o
prenotazioni. La conservazione verificata è caricato = accettato + inutilizzabile
+ residuo a bordo. `unusable` rappresenta quantità scaricata e scartata,
non una gestione implementata delle capacità di quarantena.

## Scelte tecniche introdotte in questa implementazione

Queste sono formalizzazioni locali, non nuove decisioni funzionali dell'utente.

- Tempo in secondi simulati interi, senza arrotondamento delle scadenze al tick.
  L'epoch UTC del run sarà aggiunta nel contratto completo della simulazione.
- Il cutoff è inclusivo e assume il log completo per tutti gli eventi osservati
  fino a quell'istante. Il chiamante deve chiudere il passo prima della valutazione.
- Le consegne contano dopo il controllo, a `observed_s`. `occurred_s` indica
  lo scarico fisico; un danno scoperto dopo accettazione non è gestito qui.
- Eventi simultanei ordinati per observed_s ed event_id; tutte le consegne al
  timestamp della scadenza sono considerate prima di dichiarare ritardo.
- Replica identica di event_id: nessun doppio conteggio. Stesso ID con payload
  diverso: errore. Un nuovo ID non permette di scaricare più del manifesto.
- Il filtro di osservabilità precede il replay. Le righe future non modificano
  l'esito al cutoff. Questo non sostituisce il futuro controllo della pipeline ML.
- `logistics_complete` significa assenza di residuo nei manifesti forniti;
  non attesta disponibilità reale dei veicoli o assenza di recuperi da pianificare.
- Batch associato a un solo viaggio/articolo in questo primo nucleo. Trasferimenti
  al sostituto richiederanno genealogia dei batch e movimenti dedicati.
- Un evento invalido solleva ValueError prima di restituire un risultato.
  Persistenza dello stato run invalido e quarantena dati non sono implementate.

## Esiti

Quote raggiunte: ritardo max(0, istante quote − scadenza) / 60; scadenza
inclusiva. Quote non raggiunte prima della scadenza: late e durata null.
Quote non raggiunte al termine del passo di scadenza o dopo: late true,
durata finale null. Nessuna compensazione fra articoli. L'esito resta distinto
dallo scarico del carico sopra soglia.

## Avvio e verifica

Dalla radice del repository, Python 3.11 o successivo, nessuna dipendenza extra:

```bash
python -m src.logistics.demo
python -m unittest tests.test_logistics_core -v
```

Caso: richiesta 10 ricambi piccoli e 5 grandi, soglia 90% per entrambi.
Minimi 9 e 5. Scadenza minuto 60; piccoli accettati al minuto 50;
grandi al minuto 95; ultima unità piccola al minuto 100.

| Cutoff | Obiettivo | Ritardo finale | Carico residuo |
|---|---|---|---|
| 60 min | Incompleto, ritardo certo | Sconosciuto | 1 piccolo, 5 grandi |
| 95 min | Raggiunto | 35 min | 1 piccolo |
| 100 min | Raggiunto | 35 min | Nessuno |

Verifica eseguita: 10 test unittest passati, inclusi casi di confine,
conservazione con danni, replay e idempotenza, input invalidi e cutoff.
Pytest non disponibile nell'interprete corrente: suite storica e copertura
complessiva non eseguite. Non si dichiara raggiunta la soglia del 90%.

## Passo successivo

Integrare scorte, riserve, carico e vincoli di capacità per generare il manifesto
attraverso operazioni validate; aggiungere stati viaggio e disponibilità mezzi.
Restano aperti schema completo del run, persistenza/migrazioni, annullamenti,
trasferimenti fra batch e pipeline dati/ML. P01, P02, P04 e P16 sono risolti
solo per questo sottoinsieme; F03 e S01 non sono dichiarati completi globalmente.

## Aggiornamento: blocco successivo implementato

Scorte, riserve e piani di carico sono ora disponibili in `src/logistics/warehouse.py`.
I manifesti possono essere generati dal magazzino e forniti al nucleo missioni.
Vedere [blocco-scorte-prenotazioni-carico.md](blocco-scorte-prenotazioni-carico.md)
per istruzioni, 29 test complessivi e confini esatti dell'implementazione.
