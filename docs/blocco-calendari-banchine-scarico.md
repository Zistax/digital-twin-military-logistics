# Calendari, banchine e scarico operativo — blocco completato

8 ottobre 2026. Riferimento: specifica unificata v1, sezioni 5, 7.1, 8 e 22.
Implementazione locale, senza nuove dipendenze esterne.

## Risultato consegnato

`OperationsWarehouse` estende il magazzino del blocco precedente e gestisce
carico e scarico con un unico insieme di banchine per deposito. Produce
consegne effettive per il calcolo dell'esito della missione, aggiorna le scorte
fisiche e libera il mezzo solo quando il suo carico è interamente scaricato.

| Requisito | Comportamento implementato |
|---|---|
| Calendario | Finestre settimanali, fuso locale esplicito, epoch UTC; apertura inclusiva, chiusura esclusiva |
| Arrivo a deposito chiuso | Accodamento e attesa fino alla prima apertura |
| Operazione già iniziata | Termina anche dopo chiusura, registrando i secondi fuori orario |
| Banchine condivise | Carico e scarico competono per gli stessi posti, uno per mezzo |
| Priorità | Urgenti, scadenza più vicina, ordine di creazione missione, ID viaggio come ultimo spareggio |
| Non interruzione | Nessuna preemption di un'operazione attiva |
| Riserve | Quantità in carico protette; quantità di viaggi ancora in coda riassegnabili alle urgenti |
| Spazio a destinazione | Riservato all'inizio dello scarico, contabilizzato nello stock solo alla fine |
| Scarico parziale | Solo unità che entrano, residuo a bordo; rilascio banchina e nuova ammissione quando possibile |
| Nuovo accesso | Nuovi tempi di preparazione e controllo refrigerato |
| Refrigerazione | Spazio refrigerato separato dall'ordinario; gli altri metri cubi non compensano una carenza |
| Merce inutilizzabile | Area di quarantena distinta; se piena, residuo inutilizzabile a bordo |
| Rimozione quarantena | 24 ore dopo lo scarico, alla prima apertura utile; uscita dalla rete registrata |
| Mezzi | Occupati durante attese e scarichi parziali; liberi a destinazione dopo l'ultimo scarico, riutilizzabili senza ritorno obbligatorio |
| Missioni | Consegne cumulative per articolo e quote valutate al completamento dello scarico/controllo |
| Integrità | Conservazione globale: ricevuto = stock + bordo + quarantena + rimosso |
| Operazioni ripetute | Comandi idempotenti; errori con ripristino completo dello stato |

I manifesti restano lo storico del caricato, mentre `_onboard` contiene il
residuo fisico: la conservazione non somma due volte queste quantità.
Gli snapshot sono diagnostici, non un contratto per le feature del modello.

## Interfaccia e ordine temporale

Usare la classe operativa e questi passaggi:

```python
warehouse.receive(...)        # seed o ricezione esterna già ispezionata
warehouse.register(...)
warehouse.reserve(...)
warehouse.queue_loading(...)  # piano di viaggio validato; non inizia subito
warehouse.advance(...)        # calendari, code e completamenti automatici
warehouse.depart(...)         # solo dopo il carico di tutti i mezzi
warehouse.arrive(...)         # arrivo fornito dal chiamante
warehouse.advance(...)        # scarico, stock e liberazione mezzi
warehouse.outcome(...)        # esiti dalle consegne effettivamente prodotte
```

`start_loading` e `finish_loading` manuali sono disabilitati nella classe
operativa: non permettono di saltare la gestione delle banchine.
La classe `Warehouse` originaria resta disponibile e i suoi test passano.

Ogni comando ha identificativo idempotente e istante simulato monotono.
Prima del comando vengono elaborati gli eventi precedenti e i completamenti
dovuti esattamente all'istante corrente. Inserire tutti gli input simultanei,
poi chiamare `advance` per ammetterli alle banchine secondo priorità.
Se si avanza il tempo oltre un istante, le ammissioni pendenti a quell'istante
vengono elaborate automaticamente.

Una chiamata ad `advance` che attraversa ore o giorni elabora i confini
intermedi: non salta chiusure, aperture o completamenti. Uno scarico concluso
esattamente alla scadenza è puntuale. Le query storiche escludono manifesti
caricati dopo il cutoff. Gli esiti futuri richiedono prima l'avanzamento.

## Formalizzazioni introdotte

- Code di singoli viaggi, con carichi sequenziali se ci sono poche banchine;
  la partenza della missione resta sincronizzata dopo tutti i carichi.
- Una riserva sottratta a un viaggio in coda non annulla il piano: il viaggio
  attende reintegro e nuova prenotazione. Quelli già in lavorazione terminano.
- Una volta accodato, il piano di carico è fisso; prenotazioni successive
  ripristinano il piano senza aggiungere merce non assegnata a un mezzo.
- Per scaricare merci diverse con spazio limitato si usa un ordine stabile
  di batch/articolo. Questa è una scelta tecnica deterministica, non un packing
  ottimizzato; nessun frazionamento di una singola unità.
- Le attese sono classificate senza duplicazioni: prima chiusura, poi stock,
  poi spazio, poi banchina. I secondi di marcia non sono attese di deposito.
- Le quantità inutilizzabili sono input sintetici dell'arrivo; non si estraggono
  ancora guasti o danni. Diventano consegne inutilizzabili dopo lo scarico.
- Il controllo di accettazione è incluso nella durata della movimentazione;
  non si simula un'ispezione separata con ritardo di osservazione aggiuntivo.
- Gli spazi ordinari, refrigerati e di quarantena sono riservati prima di
  avviare ogni scarico, impedendo sovraprenotazioni fra banchine parallele.
- Le finestre non attraversano la mezzanotte: dividerle in due giorni.
  Il cambio d'ora usa il calendario locale; ore ambigue aprono alla prima
  occorrenza e chiudono alla seconda. Confini in un'ora locale inesistente
  sono rifiutati esplicitamente. I normali orari 06/08–17/18/22 non hanno
  questa ambiguità in Europe/Rome.

## Demo riproducibile

Dalla radice del repository, Python 3.11+:

```bash
python -m src.logistics.operations_demo
python -m unittest tests.test_logistics_core tests.test_warehouse tests.test_operations -v
```

La demo parte lunedì 5 ottobre 2026 alle 08:00 Europe/Rome. Il deposito locale
apre alle 10:00 e può contenere cinque unità; ne arrivano dieci. La scadenza
è alle 10:20 e il minimo richiesto è nove unità.

| Ora locale | Evento prodotto |
|---|---|
| 08:00–08:10 | Carico all'origine |
| 09:00 | Arrivo al locale, ancora chiuso |
| 10:00–10:10 | Primo scarico: cinque unità |
| 10:10–10:20 | Un altro mezzo carica le cinque unità per una missione in uscita |
| 10:20–10:30 | Secondo scarico del residuo |
| 10:30 | Quote raggiunte; ritardo 10 minuti; mezzo in arrivo libero al locale |

Attese registrate per il mezzo in arrivo: 3.600 secondi per apertura e 600
per spazio. Quattro operazioni utilizzano la stessa logica di banchina.
Stock finale al locale: cinque unità; le altre cinque sono sul mezzo in uscita.
La seconda missione resta caricata, senza simulare viaggi non necessari al caso.

## Verifica

**48 test passati**: 29 preesistenti del nuovo nucleo e 19 di questo blocco.
Coprono in particolare:

- chiusura esatta, fine oltre orario, fine settimana e passaggio all'ora solare;
- priorità e impossibilità di interrompere operazioni attive;
- due scarichi paralleli che competono per lo stesso spazio;
- scarico parziale, attesa senza occupare la banchina e ripresa;
- riutilizzo del mezzo e delle merci a destinazione;
- spazio refrigerato e quarantena separati;
- rimozione dopo 24 ore rinviata se il deposito è chiuso;
- riserve dei soli carichi in corso protette dalle urgenti;
- puntualità alla scadenza esatta, idempotenza e query storiche;
- ripetibilità della demo e conservazione dopo ogni evento interno.

Nessuna dichiarazione di copertura del 90% dell'intero progetto: la suite
storica API/ML non è stata eseguita in questo ambiente.

## File e confini

- `src/logistics/calendars.py`: calendario locale settimanale.
- `src/logistics/operations.py`: banchine, code, scarico, quarantena e stock fisico.
- `src/logistics/operations_demo.py`: esempio integrato eseguibile.
- `tests/test_operations.py`: casi di accettazione.
- `warehouse.py`: aggiunto un hook transazionale per avanzare gli eventi prima
  dei comandi, con comportamento invariato nella classe base.

Restano ai blocchi successivi: rete e tempi di viaggio generati dal simulatore,
assegnazione automatica dei mezzi, rifornimenti esterni con i loro veicoli/code,
prelievi locali automatici, generazione dei danni/freddo e recuperi. `receive`
continua a essere un ingresso amministrativo di stock già controllato, non
il simulatore delle forniture esterne. La persistenza resta in memoria.
Il blocco non dichiara completo l'intero progetto né pubblica una demo online.

## Aggiornamento: arrivi generati dal trasporto

Disponibile `TransportWarehouse`, che genera gli arrivi dalla rete e assegna
automaticamente i mezzi. Vedere
[rete, trasporto e assegnazione](blocco-rete-trasporto-assegnazione.md).
La classe operativa precedente resta disponibile per prove con arrivi esterni.
