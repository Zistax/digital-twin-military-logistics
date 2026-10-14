# Rete, viaggio e assegnazione automatica — blocco completato

8 ottobre 2026. Riferimento: specifica unificata v1, sezioni 7 e 10.

## Consegna

`TransportWarehouse` integra il magazzino operativo con una rete stradale e
un assegnatore automatico. Gli arrivi derivano dai viaggi effettivamente
simulati; non sono più timestamp forniti dall'esterno.

| Funzione | Implementazione |
|---|---|
| Rete di riferimento | 25 nodi, 40 strade bidirezionali, area 100 × 100 km, seed |
| Depositi e incroci | Cinque depositi e venti incroci; un incrocio geometrico senza nodo non collega strade |
| Distanze e velocità | Distanza euclidea fra coordinate; velocità 30, 50 o 70 km/h |
| Percorsi alternativi | La rete generata rimane connessa rimuovendo qualsiasi singola strada; garantisce due percorsi senza archi condivisi |
| Routing | Minimo tempo previsto con condizioni correnti e spareggio deterministico |
| Flotta | Mezzi liberi/compatibili ordinati per tempo di raggiungimento dell'origine, poi ID |
| Trasferimento a vuoto | Tempo effettivo sulla rete, mezzo occupato; carico solo dopo arrivo all'origine |
| Multi-mezzo | Piano completo prima di assegnare; rispetto di peso, volume e refrigerazione |
| Partenza | Dopo il completamento di tutti i carichi della missione |
| Viaggio | Eventi al termine di ogni strada, anche fra tick o attraverso più strade nello stesso avanzamento |
| Cambio percorso | Al nodo successivo, solo con risparmio ≥300 secondi e ≥10% del residuo |
| Chiusura | Alternativa ammessa senza soglia di risparmio; nessun percorso disponibile → attesa al nodo |
| Arrivo | Ingresso automatico nella coda di scarico già implementata |
| Riutilizzo | Dopo scarico, mezzo libero alla destinazione, disponibile per altre missioni |
| Audit | Riserve/trasferimenti, assegnazioni, entrate/uscite dagli archi, modifiche condizioni e ricalcoli |

## Avvio

Python 3.11+, dalla radice del repository, senza dipendenze aggiuntive:

```bash
python -m src.logistics.transport_demo
python -m unittest tests.test_logistics_core tests.test_warehouse tests.test_operations tests.test_transport -v
```

Flusso minimo: `register` → `schedule` → `advance`. La ricezione dello stock
rimane esplicita. Le missioni programmate vengono gestite per urgenza, scadenza
e ordine di creazione. È possibile chiamare `advance` una sola volta o per
intervalli: il motore attraversa gli eventi intermedi e preserva gli esiti.
Gli input simultanei vanno inseriti prima di `advance`.

Il caricamento manuale tramite code resta utilizzabile; `depart` genera comunque
il viaggio. `arrive` manuale è disabilitato nella classe di trasporto.
Usare `road_condition` per aggiornamenti osservati; i campi omessi mantengono
il valore precedente. La generazione stocastica delle condizioni non è in
questo blocco.

## Scelte tecniche delimitate

### Assegnazione e composizione del carico

Packing deterministico: articoli con meno mezzi compatibili per primi, poi
volume/peso unitario decrescente; mezzi ordinati per ETA all'origine. Non viene
rivendicata un'ottimalità combinatoria. In casi di frammentazione della capacità
l'euristica può non trovare un piano che un ottimizzatore troverebbe: il motivo
è `no_feasible_greedy_plan`, non una prova di impossibilità assoluta.

Se non si trova un piano completo, nessun mezzo viene parzialmente impegnato;
le scorte restano riservate. La ricerca riparte quando il sistema avanza e
cambiano disponibilità/posizioni. L'invio a vuoto occupa i mezzi scelti; dopo
l'arrivo si rivaluta il piano con lo stato corrente, rispettando le priorità.
Le riserve in attesa rimangono riassegnabili alle urgenti.

L'annullamento durante un trasferimento a vuoto libera le riserve e i mezzi
ancora fermi. Quelli già in movimento raggiungono l'origine prevista, poi si
liberano: non vengono teletrasportati. L'annullamento di carico già impegnato
continua a richiedere il futuro flusso di recupero.

### Tempi, traffico e congestione

Formalizzazione sintetica implementativa, da verificare nel pilota:

`tempo = ceil(3600 × km / km_h × traffico × meteo × (1 + alpha × (n/C)^4))`

- Tempo in secondi interi, arrotondato per eccesso una volta per strada;
  almeno un secondo. Non si arrotonda ogni strada al passo di cinque minuti.
- `n`: altri mezzi già sulla strada nei due sensi all'ingresso.
- `C`: parametro di capacità, inizialmente 10; `alpha` inizialmente 0,15.
  Entrambi configurabili; capacità non è un limite di ingresso rigido.
- Traffico e meteo esterni restano fattori distinti dalla congestione di flotta.
- I tempi di un arco vengono fissati all'ingresso. Cambiamenti successivi
  influenzano gli archi futuri e il routing dal prossimo nodo; non riscrivono
  retroattivamente il progresso già compiuto.
- Una strada chiusa mentre il mezzo la percorre viene completata; la chiusura
  impedisce nuovi ingressi. Una chiusura fisica con mezzo bloccato a metà
  strada richiederebbe un modello diverso, non introdotto qui.

La formula e questi due parametri non sono dati reali né decisioni funzionali
approvate dall'utente: sono scelte tecniche per chiudere il primo motore.
La generazione di traffico autocorrelato, meteo imperfetto e perturbazioni
rimane da implementare. Le stime correnti non accedono a futuri eventi estratti.

### Identità, geometria e stati

Il generatore usa un ciclo che attraversa tutti i nodi più quindici strade,
per ottenere le alternative richieste. Non è una riproduzione cartografica.
Gli attraversamenti geometrici non creano adiacenze implicite.

Le strade percorse conservano nodo di ingresso, percorso residuo, istanti di
entrata/uscita e destinazione. Durante la marcia il mezzo non viene dichiarato
presente in un deposito. Una futura mappa potrà interpolare la posizione su
questi dati. La persistenza rimane in memoria.

## Demo verificata

Rete seed 17, cinque depositi con capacità/orari concordati e dieci mezzi:
quattro furgoni, quattro autocarri standard e due refrigerati. Le quattro
posizioni iniziali non fissate dalla specifica sono configurate esplicitamente
nella demo. Missione: dieci unità refrigerate dal Locale A al Centrale B,
soglia 85%, scadenza sei ore dopo l'avvio.

| Fase | Tempo simulato dall'avvio |
|---|---:|
| Mezzo `cold-b` raggiunge a vuoto il Locale A | 5.495 s |
| Fine carico e partenza | 6.395 s |
| Arrivo al Centrale B | 11.890 s |
| Fine scarico e quote raggiunte | 12.790 s |

Completamento in **3 h 33 min 10 s**, puntuale; dieci unità disponibili a
destinazione, nessuna duplicazione, mezzo liberato. Ripetendo il seed si
ottengono stessi eventi e risultati. La demo non addestra alcun modello.

## Verifica eseguita

**72 test superati**: i 48 precedenti più 24 nuovi. Fra i casi nuovi:

- riproducibilità e percorsi alternativi della rete 25/40;
- percorso più veloce anche quando non è il più corto;
- trasferimenti a vuoto, priorità, multi-mezzo e packing di merce refrigerata;
- fallimento atomico dell'assegnazione senza occupare parte della flotta;
- missione con avvio futuro;
- più archi attraversati nello stesso avanzamento;
- chiusura, attesa e riapertura senza teletrasporto;
- entrambe le soglie di rerouting verificate separatamente;
- deviazione obbligata anche se più lenta;
- stessi eventi con avanzamento unico o spezzato;
- retry, rollback e arrivi manuali vietati;
- demo completa su rete e flotta di riferimento.

La suite storica API/ML non è stata rieseguita e non si dichiara la copertura
complessiva del 90%.

## File e prossimo blocco

- `src/logistics/roads.py`: rete, generatore e routing.
- `src/logistics/transport.py`: assegnazione e viaggi integrati.
- `src/logistics/transport_demo.py`: esempio completo.
- `tests/test_transport.py`: test.
- `operations.py`: hook per includere gli eventi stradali nel motore temporale.

Prossimo blocco: forniture esterne, prelievi locali, arretrati e riordino.
Seguono imprevisti/recuperi e generatori dei profili; la pipeline ML e la UI
non sono ancora collegate a questo nuovo nucleo. Nessun push o deploy eseguito.

## Aggiornamento: forniture e domanda locale

Disponibile `SupplyWarehouse`: ordini esterni, prelievi, arretrati e riordino.
Vedere [forniture, prelievi e riordino](blocco-forniture-prelievi-riordino.md).
Le verifiche del nucleo comprendono ora 90 test.
