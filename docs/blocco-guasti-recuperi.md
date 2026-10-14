# Guasti, refrigerazione, danni e recuperi — incremento 6

Aggiornato il 13 ottobre 2026. Roadmap: **S05**, ottava voce delle diciotto previste.
Stato: perimetro funzionale S05 implementato e verificato. Restano i limiti
sperimentali dichiarati in fondo; il passo successivo è S06.

## Cosa funziona

| Funzione | Comportamento verificato |
|---|---|
| Guasto riparabile | Ferma il mezzo nella posizione raggiunta sull'arco; conserva il tratto residuo e riparte dopo la riparazione |
| Guasto non riparabile | Mezzo indisponibile e richiesta di sostituzione; nessun trasferimento senza approvazione |
| Sostituto | Libero e compatibile; può recuperare solo una parte del carico e raggiunge il punto di guasto attraverso un estremo della strada e il tratto residuo |
| Trasferimento | Setup di 10 minuti più scarico/carico degli articoli; mantiene le quantità; il recupero parziale crea viaggi e batch figli tracciati |
| Rientro mezzo guasto | All'origine del viaggio, dopo il tempo di servizio esterno e solo quando il carico è stato gestito |
| Refrigerazione | Allarme immediato, esposizione cumulativa per batch anche durante soste; nessun azzeramento al ripristino o cambio mezzo |
| Deterioramento | Superata la tolleranza, danno nello stato interno; quantità confermate dopo ispezione |
| Movimentazione | Danni per unità sana e per operazione; unità già danneggiate non conteggiate due volte |
| Ispezione | Accettato e inutilizzabile distinti; quarantena piena lascia il residuo sul mezzo |
| Integrazione | Dopo gli scarichi, proposta solo per il deficit rispetto alla quota, senza ripristinare automaticamente il 100% |
| Identità missione | Consegne integrative sulla stessa missione e scadenza; nuovi viaggi e batch solo per nuova merce |
| Decisioni | Approva, rinvia e rifiuta, con storico; rifiuto distinto da annullamento |
| Annullamento | Libera riserve e mezzi non impegnati; carico già avviato continua alla destinazione originale e viene scaricato |
| Batch | Approvazioni riproducibili con attese urgenti 5–15 minuti, ordinarie 15–60 |
| Fornitori | Comando per campionare ritardi e quantità incomplete; atteso distinto dall'effettivo |

Le richieste di recupero ancora aperte impediscono di indicare la missione
come logisticamente chiusa. L'esito dopo annullamento è distinto e non riceve
artificialmente un'etichetta di ritardo finale.

## Formalizzazioni implementative

- `IncidentPolicy` sceglie seed, profilo regolare/sotto pressione/perturbato,
  generazione automatica, approvazione batch e tolleranza frigorifera.
- In assenza di attivazione esplicita gli imprevisti non sono estratti:
  i comandi deterministici permettono casi di prova controllati.
- In modalità automatica la categoria è obbligatoria per ogni articolo:
  `food`, `cold`, `medical`, `spares`, `electronics`.
- Tempi al guasto ottenuti da orologi esponenziali: tasso
  `-log(1-p_oraria)/3600`. Il guasto meccanico consuma solo tempo effettivo
  di marcia; l'impianto frigorifero usa tempo di funzionamento anche in sosta.
- Le durate e le approvazioni sono estratte uniformemente fra i multipli di
  cinque minuti nell'intervallo approvato. È una scelta sperimentale esplicita.
- Il ripristino esterno automatico usa 24–48 ore. I comandi di test accettano
  durate diverse per esercitare i vincoli senza simulare giornate intere.
- Un batch iniziale mantiene una storia di esposizione omogenea. Un nuovo
  viaggio integrativo crea un nuovo batch; la sostituzione integrale mantiene
  quello vecchio, quella parziale crea un figlio con storia ereditata.
- Il danno da carico è conservato internamente sino al controllo allo scarico.
  La selezione iniziale della banchina non vede quel danno futuro; se al controllo
  la quarantena non basta, la parte inutilizzabile resta a bordo.
- Il trasferimento considera due movimentazioni (scarico e carico): setup
  unico di 600 secondi più due volte il tempo degli articoli, arrotondato una
  volta al passo. L'esposizione durante il trasferimento usa l'impianto del
  mezzo cedente fino al completamento; un modello fisico diverso resta aperto.
- Per l'annullamento viene mantenuta la destinazione già pianificata del
  carico impegnato. È una scelta conservativa per il dettaglio P19; il sistema
  non cerca automaticamente un nuovo deposito di rientro.
- L'incompletezza di una fornitura è un evento dell'ordine; se si verifica,
  ogni articolo riceve una frazione indipendente nell'intervallo approvato,
  arrotondata per difetto. Una nuova validazione reale dovrà sostituire queste
  distribuzioni sintetiche.

`observed_incidents()` restituisce allarmi, ispezioni e richieste osservate,
senza gli istanti futuri di approvazione o le quantità danneggiate nascoste.
Gli snapshot completi restano diagnostici: non sono feature ML utilizzabili
senza un ulteriore contratto temporale.

## Demo e test

Dalla radice del repository, Python 3.11+:

```bash
python -m src.logistics.recovery_demo
python -m unittest tests.test_logistics_core tests.test_warehouse tests.test_operations tests.test_transport tests.test_supply tests.test_recovery -v
```

Demo: richieste 10 unità, quota 90%, scadenza al secondo 2.500.

| Istante simulato | Evento |
|---|---|
| 1.000 s | Due unità danneggiate internamente; guasto non riparabile |
| 1.100 s | Approvata la sostituzione |
| 2.700 s | Trasferimento al sostituto completato |
| 4.100 s | Ispezione: 8 unità accettate, 2 inutilizzabili; proposta di integrazione da 1 |
| 4.100 s | Approvata l'integrazione |
| 7.700 s | Nona unità accettata; quota raggiunta con 86 minuti e 40 secondi di ritardo |
| 87.400 s | Mezzo originale ripristinato al deposito di origine |

Nessuna modifica della scadenza e nessuna duplicazione di carico. Il sostituto
ritorna fisicamente all'origine per prelevare l'unità aggiuntiva. Stock finale:
9 all'origine, 9 alla destinazione e 2 in quarantena, su 20 iniziali.

**129 test passati**, di cui 39 nel modulo recuperi. Comprendono conservazione, ripartenza
dopo riparazione, recupero approvato, ritardo del rientro finché c'è carico,
deficit minimo, rifiuto/rinvio, caldo cumulativo oltre la soglia, conservazione
dell'esposizione al cambio mezzo, quarantena satura, retry, annullamento,
ripetibilità e coerenza degli orologi con avanzamenti temporali spezzati.

## Estensione verificata il 13 ottobre

- `Item.cold_tolerance_s` permette una soglia intera non negativa per articolo
  refrigerato. Se omessa usa `IncidentPolicy.tolerance_s`; la merce si deteriora
  soltanto oltre la soglia. Articoli sullo stesso mezzo possono avere esiti diversi.
- Lo scarico esterno applica il rischio per categoria alle sole unità sane,
  con un flusso casuale dedicato a ordine/articolo. La modalità deterministica
  mantiene danno nullo salvo fixture esplicite.
- Il materiale inutilizzabile entra nella quarantena compatibile. Se lo spazio
  non basta, resta al fornitore e la banchina si libera. Il residuo già danneggiato
  non viene nuovamente campionato e non conta come approvvigionamento utilizzabile.
- La rimozione avviene dopo 24 ore dall'ingresso, alla prima apertura utile,
  usando lo stesso ciclo della merce scaricata dalla flotta interna.
- `received` conta il totale fisicamente scaricato, `unusable` la sua parte in
  quarantena; l'accettato è la differenza. `not_delivered` misura invece la
  mancanza all'arrivo e non incorpora danni di movimentazione.
- Il registro `supply_unload` distingue `accepted` e `unusable`. Sono verificati
  conservazione sia interna sia del carico esterno e avanzamenti temporali
  spezzati equivalenti a un unico avanzamento.

## Guasti del soccorritore

- L'avvicinamento finale consuma l'orologio meccanico come il viaggio sulla
  rete. Il rischio automatico resta proporzionale al solo tempo di marcia.
- Un guasto riparabile sospende l'avvicinamento o il trasferimento e conserva
  il tempo residuo. L'interruzione del trasferimento è iniettabile esplicitamente;
  non viene estratto un rischio di marcia mentre il mezzo è fermo.
- Un soccorritore non riparabile abbandona il tentativo. La richiesta torna
  approvata, mantenendo la decisione già registrata, e cerca un mezzo libero.
  Il soccorritore guasto resta indisponibile fino al rientro dal servizio esterno.
- Il carico resta interamente sul mezzo cedente fino alla conclusione atomica
  del trasferimento. Un tentativo abbandonato non crea merce o nuovi manifesti.
- Sono verificati guasti durante il viaggio all'estremo stradale, avvicinamento,
  trasferimento, secondo guasto dopo il recupero, annullamento durante la
  riparazione e orologi automatici invarianti rispetto alla partizione del tempo.

## Recupero frazionato e genealogia

Se nessun mezzo libero può trasportare tutto il residuo, il motore sceglie
un mezzo compatibile per una frazione. I trasferimenti dal mezzo guasto sono
sequenziali; i viaggi dei carichi già trasferiti possono procedere in parallelo.
È possibile riutilizzare lo stesso mezzo piccolo dopo lo scarico e il ritorno
fisico al punto di recupero. Non serve una nuova approvazione per ogni frazione.

La selezione è euristica: preferisce un sostituto capiente, altrimenti il mezzo
con minore tempo di arrivo fra quelli che portano almeno un'unità. Non ottimizza
il tempo globale di recupero né prenota una squadra di mezzi simultaneamente.

Ogni frazione riceve un viaggio e un batch figlio. `batch_splits` registra
missione, istante, chiave del genitore, chiave del figlio e quantità. Il manifesto
corrente redistribuisce il carico senza duplicarlo; `outcome` ricostruisce anche
i manifesti storici, annullando i frazionamenti posteriori al tempo richiesto.
Il carico residuo mantiene il batch originario. Esposizione al caldo e danni
sono conservati; per ripartire i danni nascosti si assegna prima la parte già
danneggiata alla frazione trasferita. È una convenzione sintetica esplicita,
non una selezione informata dell'operatore, che non vede i danni nascosti.

Il mezzo originario resta indisponibile finché tutto il suo carico è stato
trasferito. La missione termina logisticamente solo dopo tutti gli scarichi,
compresi i viaggi figli. Restano invariati missione, scadenza e quote minime.

Sono verificati recupero con due sostituti, riutilizzo di un solo mezzo piccolo,
più articoli, danni e integrazione successiva, eredità dell'esposizione, guasto
di un viaggio figlio con ulteriore frazionamento, annullamento e ricostruzione
storica. Gli avanzamenti temporali spezzati producono gli stessi esiti.

## Limiti e lavoro successivo

Il perimetro operativo S05 è coperto dai test deterministici. Il prossimo blocco
è S06, generatore dei tre profili e arresto degli esperimenti. La validazione
statistica e le combinazioni su molte simulazioni appartengono al pilota D02.
Impianti frigoriferi dei depositi e danni dopo accettazione restano decisioni
funzionali P02/P20 di F01; non sono introdotti implicitamente in questo nucleo.

Il motore non è dichiarato validato per il lotto da 90 simulazioni. Non sono
stati eseguiti la suite storica API/ML o il controllo di copertura globale.
Nessun push o deploy.

File: `incidents.py`, `recovery.py`, `recovery_demo.py`,
`tests/test_recovery.py`; hook temporale in `operations.py`.
Per il quadro completo vedere [stato-roadmap.md](stato-roadmap.md).
