# Blocco scorte, prenotazioni e carico — completato

Data: 8 ottobre 2026. Riferimento: Specifica unificata v1, sezioni 6.1,
7.3 e 8.1. Implementazione locale nel repository; nessun push effettuato.

## Risultato

Il flusso disponibile è ricezione di merce già controllata → registrazione
missione → riserva → piano manuale su uno o più mezzi → inizio carico →
completamento carico → partenza sincronizzata → valutazione delle consegne
esterne con il nucleo missioni precedente.

Questo blocco completa la gestione transazionale delle scorte e del carico;
non dichiara completati S02/S03 dell'intera roadmap, che comprendono anche
calendari, banchine, assegnazione automatica e rete stradale.

## Funzioni e garanzie verificate

| Funzione | Comportamento |
|---|---|
| Catalogo e capacità | Peso/volume Decimal finiti; quantità intere; volumi ordinari e refrigerati separati |
| Ricezione | Solo merce utilizzabile e già controllata; superare una capacità rifiuta tutta l'operazione |
| Prenotazione | Stock fisico invariato; disponibile = fisico − riservato; richieste ripetute non duplicano le riserve |
| Missione ordinaria | Carico avviabile solo con il 100% riservato per ogni articolo |
| Missione urgente | Carico avviabile con il minimo di ogni articolo; nessuna compensazione fra articoli |
| Riassegnazione | Urgenti possono ricevere riserve di ordinarie non in carico; donatori e quantità tracciati |
| Protezione | Tutte le quantità del piano sono protette dall'inizio del carico |
| Annullamento prima del carico | Rilascia tutte le riserve; annullamento con carico iniziato respinto in attesa del flusso di recupero |
| Piano multi-mezzo | Veicoli già all'origine, liberi, unici, compatibili; peso e volume rispettati; copertura esatta della riserva |
| Movimentazione | 5 minuti setup + somma tempi per unità + 5 minuti se refrigerato; arrotondamento unico al passo |
| Completamento carico | Consuma stock e riserva una volta sola; genera batch e manifesti utilizzabili dal replay missioni |
| Partenza | Tutti i mezzi della missione hanno completato il carico; nessuna partenza anticipata |
| Integrità | Ricevuto = stock nei depositi + caricato nei manifesti, verificato dopo ogni comando |
| Retry | Identico ID e contenuto restituiscono il risultato precedente; contenuto diverso con stesso ID respinto |
| Errore | Ripristino di tutto lo stato del comando, inclusi mezzi, stock, audit e orologio |
| Diagnostica | Snapshot separati dallo stato interno, registro dei comandi riusciti e dei trasferimenti di riserva |

## Decisioni tecniche per questo blocco

- Comandi manuali espliciti e cronologici in secondi simulati. Chiavi idempotenti
  uniche nell'istanza; un retry identico resta valido dopo comandi successivi.
- Per donatori multipli, si preleva prima dalle ordinarie con scadenza più lontana,
  poi dalle più recenti. È un criterio implementativo deterministico, non una
  modifica delle priorità approvate. Non si preleva da altre urgenti.
- La prenotazione cerca fino al 100% anche per l'urgente; la soglia abilita il
  carico se la disponibilità resta parziale.
- Il piano copre l'intera riserva della missione. Tutti i carichi nel piano
  iniziano insieme; la partenza attende l'ultimo. L'ammissione alle banchine
  dovrà sostituire questa condizione nel blocco calendari/code.
- Durante il carico la merce resta nello stock riservato/protetto; il trasferimento
  nel manifesto avviene al completamento. Non si modellano quantità intermedie
  durante l'operazione.
- La capacità della destinazione viene verificata come compatibilità del singolo
  articolo; non si prenota ancora spazio di arrivo.
- `receive` rappresenta una ricezione accettata, non un ordine o un arrivo futuro.
- `evaluate` usa consegne ispezionate esterne e non modifica il magazzino di
  destinazione né libera i mezzi. I manifesti rappresentano il carico iniziale;
  il replay calcola il residuo. Non sommare il suo risultato allo stock come
  se fosse una seconda contabilizzazione.
- Stato e audit sono in memoria. La copia per rollback privilegia la correttezza
  del primo blocco; persistenza e prestazioni del lotto completo non sono validate.

## Avvio

Dalla radice del repository con Python 3.11 o successivo, senza dipendenze extra:

```bash
python -m src.logistics.warehouse_demo
python -m unittest tests.test_logistics_core tests.test_warehouse -v
```

La demo carica 10 unità medie e 5 grandi su due mezzi. I manifesti derivano
realmente dalle scorte, senza inserirli manualmente. Entrambi i carichi terminano
al minuto 15; gli eventi di consegna successivi sono prefissati per isolare
il comportamento del blocco.

| Istante | Risultato |
|---|---|
| Minuto 15 | Stock all'origine azzerato; due manifesti prodotti, partenza abilitata |
| Minuto 60 | Missione incompleta, ritardo certo, durata finale non conosciuta |
| Minuto 95 | Quote raggiunte, ritardo 35 minuti, una unità media ancora a bordo |
| Minuto 100 | Tutto consegnato nel replay; ritardo invariato a 35 minuti |

## Verifica eseguita

29 test passati: 10 del nucleo missioni e 19 del nuovo blocco. Coprono anche
rifiuto atomico del secondo mezzo in un piano, stock al limite della capacità,
merce refrigerata, annullamenti, riassegnazioni protette, doppio completamento,
timing, isolamento degli snapshot e ripetibilità della demo.

Verificato il caso della specifica con un unico carico di 10 medi + 5 grandi:
25 minuti complessivi. Verificato che 9 unità piccole da 30 secondi ciascuna
richiedano 10 minuti incluso setup/arrotondamento, non 50 minuti.

La suite storica del prototipo non è stata rieseguita; non è dichiarata la
copertura del 90% dell'intero progetto. Nessuna dipendenza aggiunta, nessuna
modifica al modello ML/API storici o ai dati preesistenti.

## File

- `src/logistics/warehouse.py`: contratti, stock, comandi e integrazione.
- `src/logistics/warehouse_demo.py`: demo riproducibile.
- `tests/test_warehouse.py`: verifiche del blocco.

Passo successivo: calendari e banchine, code, scarico con capacità e liberazione
dei mezzi. Rifornimenti automatici, domanda locale, routing, guasti e ML restano
nei rispettivi blocchi della specifica.

## Aggiornamento: calendario e scarico integrati

Il blocco successivo è disponibile in `OperationsWarehouse`:
[calendari, banchine e scarico operativo](blocco-calendari-banchine-scarico.md).
Supera nella classe operativa la precedente ammissione simultanea senza banchine,
aggiunge stock a destinazione e rilascio mezzi; la classe base resta invariata
per compatibilità. Le verifiche del nuovo nucleo sono ora 48.
