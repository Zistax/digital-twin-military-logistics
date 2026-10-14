# Logistica predittiva — Specifica unificata della prima versione

**Versione documento:** 1.0 — 8 ottobre 2026  
**Destinatario:** Tiziano Salvatori  
**Stato:** consolidamento delle decisioni approvate; non attestazione di software completato.  
**Titolo descrittivo:** piattaforma sperimentale di simulazione, analisi e previsione dei ritardi logistici.

## 1. Autorità, fonti e lettura del documento

Questa specifica raccoglie le decisioni prese nella conversazione del 7–8 ottobre 2026. Le decisioni più recenti prevalgono sui documenti originali del 7 novembre 2025 quando esiste un conflitto. I file originali non sono stati sovrascritti; questo documento costituisce un nuovo riferimento consolidato.

Fonti testuali rilette: README principale («README (1).md»), README indice, project_summary.txt e i dodici capitoli originali da 01-visione-e-slo a 12-etica-terminologia-licensing. I diagrammi storici non costituiscono requisiti della nuova versione: devono essere aggiornati alle regole qui raccolte. Non vengono incorporati come rappresentazione del nuovo sistema.

Tre livelli di informazione:

- **Decisione approvata:** requisito o parametro esplicitamente concordato nella conversazione.
- **Formalizzazione:** notazione, identificativi proposti e conseguenze necessarie delle regole approvate; non modifica del loro significato.
- **Da definire:** dettaglio non ancora deciso o da risolvere in implementazione. È raccolto nella sezione 23; non deve essere presentato come già approvato.

Tutti i numeri del simulatore sono ipotesi sintetiche configurabili. Non rappresentano statistiche del mondo reale, standard di conservazione o un dimensionamento già validato. Ogni modifica successiva deve essere versionata e motivata attraverso il pilota o un esperimento documentato.

## 2. Obiettivo e perimetro

### 2.1 Obiettivo centrale

Realizzare un progetto da portfolio professionale, utile per mostrare competenze di analisi dati, qualità, simulazione e machine learning, con basi riutilizzabili per una futura integrazione di dati reali.

La domanda principale è:

> Questa missione raggiungerà le quote minime richieste entro la scadenza? Se sarà tardiva, di quanto?

La previsione è centrale. L'analisi serve a costruirla, interpretarla e verificarla: non è una funzionalità marginale. La prima versione usa merci generiche, rete sintetica e dati sintetici, senza integrazione con operazioni reali. Il nome storico del repository non cambia questo perimetro sperimentale.

### 2.2 Incluso nella prima versione completa

- Creazione manuale e generazione automatica di missioni.
- Merci miste: cinque categorie, tre articoli/formati per categoria.
- Magazzini centrali e depositi locali con capacità, scorte, code e calendari.
- Flotta condivisa; più mezzi e viaggi per missione.
- Rete sintetica, condizioni variabili e ricalcolo del percorso.
- Forniture esterne, trasferimenti interni, prelievi locali e arretrati.
- Guasti, danni, interruzioni frigorifere, recuperi e quarantena.
- Approvazioni effettive in modalità interattiva e simulate negli esperimenti.
- Previsioni prima dell'avvio e durante la missione, intervalli e astensione.
- Dataset validati, analisi dei KPI, baseline e valutazione indipendente.
- Quattro viste della dashboard; versione locale riproducibile e demo online limitata.

### 2.3 Fase successiva e limiti

La RL è rinviata alla seconda fase. Il modello della prima versione è informativo: non comanda automaticamente mezzi, scorte o priorità. Le azioni automatiche seguono le regole concordate; quelle manuali sono registrate.

L'applicabilità reale richiederà dati reali e una nuova validazione di ipotesi, parametri e prestazioni. Non è deducibile dall'accuratezza su dati sintetici. La disposizione geometrica degli imballaggi, il dettaglio di officine/soccorso e i mezzi dei fornitori esterni non sono simulati nella prima versione.

## 3. Missioni, obiettivo di consegna e ritardo

### 3.1 Definizione di missione

Ogni missione ha un identificativo proprio, un'origine e una destinazione diverse, un avvio programmato, una scadenza liberamente impostabile successiva all'avvio, un'urgenza e una lista di articoli con quantità richieste e quote minime.

Sono ammesse da una a cinque categorie compatibili con i depositi; non è necessario includerle tutte. Il riferimento quantitativo è sempre la richiesta iniziale, mai il carico effettivamente partito.

L'avvio coincide con l'inizio della missione, anche se attende scorte o mezzi, non con la partenza del veicolo. Il tempo della missione include attesa della merce, assegnazione/raggiungimento dell'origine, code, carico, viaggio, scarico e controlli.

Quantità, categorie, soglie, origine, destinazione, scadenza e urgenza sono modificabili solo prima dell'avvio. Ogni modifica aggiorna prenotazioni e previsioni conservando lo storico. Dopo l'avvio rimangono consentite le azioni operative concordate, incluso annullamento esplicito.

### 3.2 Quote per articolo

Ogni categoria ha una percentuale predefinita, modificabile in pianificazione. La percentuale si applica separatamente a ciascun articolo richiesto della categoria; non è ammessa compensazione fra articoli o formati diversi.

Formalizzazione: per articolo i, quantità richiesta intera Q_i > 0 e soglia s_i, il minimo richiesto è M_i = ceil(Q_i × s_i). D_i(t) è la quantità cumulativa scaricata, controllata e utilizzabile consegnata per quella missione entro t.

L'obiettivo è raggiunto quando, per tutti gli articoli richiesti, D_i(t) ≥ M_i. Articoli assenti non contribuiscono al criterio. Due colli piccoli non sostituiscono automaticamente un collo medio.

Esempio: 10 casse piccole di ricambi e 5 grandi, entrambe al 90%, richiedono almeno 9 piccole e 5 grandi.

### 3.3 Esito temporale e fine delle attività

Il tempo di raggiungimento delle quote T_quote è il primo istante in cui tutti i minimi sono soddisfatti. Con scadenza D:

- obiettivo temporale rispettato se T_quote ≤ D;
- ritardo finale = max(0, T_quote − D), espresso in minuti;
- ritardo per articolo calcolato sul primo raggiungimento del suo minimo.

Una missione che raggiunge tutte le quote è conclusa rispetto all'obiettivo, anche sotto il 100% della richiesta. Distinguere nell'analisi successo con consegna completa e successo con consegna parziale. Le unità non caricate restano all'origine; non nasce automaticamente un recupero del residuo sopra soglia.

Se rimane carico già in viaggio, i viaggi proseguono fino allo scarico. I mezzi rimangono occupati fino al termine delle loro operazioni. Occorre distinguere T_quote dalla fine logistica di tutti i viaggi: non ritardare artificialmente l'esito predittivo per attendere merce eccedente le quote.

Superata la scadenza, la consegna prosegue. L'esito temporale negativo non viene riscritto come positivo dopo l'arrivo tardivo. La quota raggiunta esattamente alla scadenza è puntuale.

### 3.4 Missioni aperte e annullate

Alla fine del periodo osservato:

| Stato | Informazione disponibile |
|---|---|
| Quote non raggiunte, scadenza futura | Esito temporale ancora sconosciuto |
| Quote non raggiunte, scadenza raggiunta/superata dopo il controllo degli eventi dovuti | Ritardo certo, durata finale sconosciuta |
| Quote raggiunte | Esito e ritardo finale conosciuti |
| Annullamento | Stato distinto, motivazione e quantità già consegnate conservate |

Non assegnare ritardo finale zero, un valore inventato o il limite della simulazione alle osservazioni incomplete. Non trattare indiscriminatamente gli annullamenti come consegne tardive: la regola di inclusione nel training va esplicitata (sezione 23).

## 4. Catalogo merci

### 4.1 Categorie e soglie

| Categoria | Quota predefinita |
|---|---:|
| Alimenti non refrigerati | 80% |
| Prodotti refrigerati | 85% |
| Materiale sanitario non refrigerato | 95% |
| Ricambi meccanici | 90% |
| Apparecchiature elettroniche | 75% |

Le quote rappresentano requisiti sintetici del destinatario, non probabilità di danno o indicazioni per la gestione di beni reali. La soglia inferiore dell'elettronica assume forniture frazionabili; non deriva dalla fragilità. In futuro i requisiti reali dovranno essere rilevati per articolo.

### 4.2 Quindici articoli iniziali

Peso e volume includono l'imballaggio. Ogni formato è un articolo distinto, indivisibile, con unità intere.

| Categoria | Piccolo: kg / m³ | Medio: kg / m³ | Grande: kg / m³ |
|---|---:|---:|---:|
| Alimenti non refrigerati | 5 / 0,02 | 10 / 0,04 | 20 / 0,08 |
| Prodotti refrigerati | 5 / 0,025 | 10 / 0,05 | 20 / 0,10 |
| Materiale sanitario non refrigerato | 2 / 0,02 | 5 / 0,04 | 10 / 0,08 |
| Ricambi meccanici | 10 / 0,025 | 25 / 0,06 | 50 / 0,12 |
| Apparecchiature elettroniche | 3 / 0,03 | 10 / 0,10 | 25 / 0,25 |

Articoli configurabili per peso, volume, conservazione, fragilità e tempi di movimentazione. Le somme di peso e volume determinano l'ammissibilità del carico; non è prevista ottimizzazione geometrica del vano. Unità danneggiate sono inutilizzabili e non contano come consegnate valide.

## 5. Depositi e calendari

### 5.1 Capacità iniziali

| Deposito | Ordinario | Refrigerato | Banchine condivise carico/scarico | Quarantena ordinaria | Quarantena refrigerata |
|---|---:|---:|---:|---:|---:|
| Centrale A | 1.000 m³ | 200 m³ | 3 | 20 m³ | 5 m³ |
| Centrale B | 800 m³ | 150 m³ | 3 | 20 m³ | 5 m³ |
| Locale A | 200 m³ | 50 m³ | 1 | 5 m³ | 2 m³ |
| Locale B | 150 m³ | 0 | 1 | 5 m³ | 0 |
| Locale C | 100 m³ | 0 | 1 | 5 m³ | 0 |

Le aree di quarantena sono aggiuntive e separate. Ogni banchina serve un mezzo alla volta. Capacità di stoccaggio, numero di banchine e velocità di movimentazione sono concetti separati.

Prodotti refrigerati richiedono origine e destinazione attrezzate. Lo spazio ordinario non compensa automaticamente una carenza di refrigerato e viceversa. Il catalogo e le richieste devono essere verificati in pianificazione.

### 5.2 Calendari

| Struttura | Apertura iniziale |
|---|---|
| Centrali A e B | Tutti i giorni, 06:00–22:00 |
| Locale A | Lunedì–sabato, 08:00–18:00 |
| Locali B e C | Lunedì–venerdì, 08:00–17:00 |

Calendari configurabili, inclusa apertura 24/7. Fuori orario i mezzi possono arrivare ma non iniziano carico/scarico. Le operazioni iniziate terminano anche oltre chiusura; registrare il tempo aggiuntivo. Gli impianti frigoriferi restano attivi a deposito chiuso.

Registrare separatamente attesa per apertura, spazio e banchina. Le forniture diventano disponibili dopo scarico e verifica, non al semplice arrivo al cancello.

## 6. Scorte, prenotazioni, rifornimenti e domanda locale

### 6.1 Stati delle scorte

- Disponibile: fisicamente presente, utilizzabile e non riservata.
- Riservata: fisicamente presente ma assegnata a una missione.
- In arrivo: prevista, non caricabile finché non ricevuta e scaricata.
- Quarantena: fisicamente presente in area dedicata, inutilizzabile.

Disponibile e riservata sono parti dello stock fisico utilizzabile, non quantità da sommare due volte. Il carico sottrae stock fisico e consuma la prenotazione. L'annullamento prima del carico libera le riserve.

Una missione urgente può ricevere riserve di una ordinaria non ancora caricate. Le quantità coinvolte in un carico già iniziato sono protette. La riassegnazione è tracciata; la missione privata della merce torna in attesa senza spostare la propria scadenza.

### 6.2 Ordine di assegnazione della nuova merce

1. Missioni urgenti.
2. Richieste locali arretrate, dalla più vecchia.
3. Missioni ordinarie, per scadenza e poi ordine di creazione.

Riserve esistenti protette salvo l'eccezione delle urgenti. Misurare eventuali attese sistematiche delle richieste meno prioritarie.

### 6.3 Scorte iniziali

- Centrali: circa 3 giorni di domanda prevista per articolo.
- Locali: circa 1 giorno di domanda prevista per articolo.
- Domanda = spedizioni previste in uscita + prelievi locali previsti.
- Calcolo dai parametri generativi, non dalla conoscenza delle richieste future estratte.
- Capacità e compatibilità fisiche sempre rispettate; limitazioni segnalate e quantità inizializzate registrate.
- Nei confronti iniziali, profili sotto pressione e perturbato partono dalle scorte del profilo regolare.

### 6.4 Rifornimenti

Trasferimenti interni: normali missioni tra depositi, con flotta condivisa, sottrazione all'origine e ingresso dopo scarico a destinazione. Forniture esterne: arrivi programmati con quantità/orari previsti ed effettivi separati; i veicoli esterni non vengono simulati in dettaglio.

Sono incluse modalità programmata e automatica su soglia, anche combinate.

| Deposito | Soglia d'ordine | Livello obiettivo | Tempo previsto di fornitura |
|---|---:|---:|---:|
| Centrale | Sotto 1,5 giorni di copertura | 3 giorni | 24 ore |
| Locale | Sotto 0,5 giorni di copertura | 1 giorno | 12 ore |

Controllo per articolo considerando scorte, impegni, arretrati e ordini aperti. Non duplicare domanda né ordini già coperti da arrivi programmati. Ritardi e incompletezze modificano l'esito della fornitura; fuori orario si attende lo scarico.

Una fornitura esterna parziale si chiude registrando il residuo come non consegnato. Il residuo non resta falsamente in arrivo; un nuovo ordine può essere generato dal controllo delle scorte.

### 6.5 Prelievi locali

Rappresentano consumo/distribuzione all'esterno della rete. Una richiesta giornaliera per deposito, all'orario nominale di apertura; nei giorni chiusi resta in attesa. Interessa gli articoli gestiti.

Quantità iniziale per articolo: 10–30% della domanda media giornaliera prevista delle spedizioni in uscita, con seed e arrotondamento per eccesso. Prima si stima la domanda di spedizione, poi quella locale, infine il totale usato per scorte e rifornimenti: nessuna dipendenza circolare.

I prelievi usano solo merce disponibile, non riservata. Soddisfazione parziale ammessa; il residuo resta in arretrato fino a completamento. Registrare richiesto, prelevato, residuo e attesa. Lo stock e il volume occupato diminuiscono al prelievo.

## 7. Flotta, assegnazione e viaggi

### 7.1 Flotta iniziale

| Tipo | Numero | Portata individuale | Volume individuale | Compatibilità |
|---|---:|---:|---:|---|
| Furgone | 4 | 1.000 kg | 8 m³ | Non refrigerato |
| Autocarro standard | 4 | 8.000 kg | 40 m³ | Non refrigerato |
| Autocarro refrigerato | 2 | 5.000 kg | 30 m³ | Refrigerato e merci compatibili con la temperatura |

Dieci mezzi totali. Un furgone, uno standard e uno refrigerato inizialmente in ciascun centrale; i restanti due furgoni e due standard distribuiti fra i tre locali. L'assegnazione esatta degli ultimi quattro resta configurativa.

Flotta condivisa, posizione aggiornata, nessun ritorno obbligatorio. Il trasferimento a vuoto verso l'origine richiede tempo. Dopo lo scarico il mezzo è libero a destinazione. Un mezzo non può appartenere contemporaneamente a due missioni; una missione può avere più mezzi e viaggi fin dall'inizio.

### 7.2 Assegnazione

Automatica: scegliere mezzi liberi e compatibili, preferendo quelli con minor tempo di raggiungimento dell'origine; assegnarne quanto serve rispettando peso/volume. Se insufficienti, la missione attende con motivo registrato.

Manuale: stessi controlli di disponibilità, compatibilità e capacità. Un piano presumibilmente tardivo genera avviso ma resta eseguibile. Tracciare modalità e motivazione dell'assegnazione. L'algoritmo preciso di composizione della flotta e i pareggi tecnici sono da specificare.

Precedenza per nuove assegnazioni e code: urgenti, scadenza più vicina, ordine di creazione. Nessuna interruzione delle operazioni già iniziate.

### 7.3 Partenza e carichi parziali

Ordinaria: attende la disponibilità del 100% del carico richiesto. Urgente: può partire se ogni articolo raggiunge almeno il minimo derivato dalla soglia della categoria. La condizione riguarda l'intera missione; la sincronizzazione esatta delle partenze dei singoli mezzi va formalizzata.

La partenza al minimo non abbassa l'obiettivo e lascia poco o nessun margine ai danni. Quantità ricevute da viaggi diversi si sommano senza duplicazioni.

## 8. Carico, scarico, saturazione e quarantena

### 8.1 Tempi iniziali

| Componente | Durata |
|---|---:|
| Preparazione per accesso alla banchina | 5 minuti |
| Unità piccola | 0,5 minuti |
| Unità media | 1 minuto |
| Unità grande | 2 minuti |
| Controllo aggiuntivo refrigerato, se presente | 5 minuti per operazione |

Tempi configurabili per articolo e deposito, differenziabili fra carico e scarico. Sommare i tempi prima di applicare la risoluzione temporale; non arrotondare ogni collo a cinque minuti. Esempio: 10 medi + 5 grandi = 25 minuti incluso setup, senza refrigerato.

### 8.2 Scarico parziale

Se manca spazio, scaricare quanto compatibile e disponibile. Le quantità scaricate utilizzabili contano subito verso le quote. Residuo sul mezzo, refrigerazione attiva e mezzo ancora occupato. Liberare la banchina, sostare in attesa, rientrare in coda quando è disponibile spazio. Ogni nuovo accesso comporta nuova preparazione.

### 8.3 Quarantena

Merce dichiarata inutilizzabile separata dallo stock. Se l'area di quarantena è piena, merce sul mezzo in attesa senza trattenere la banchina. Rimozione dopo 24 ore dall'ingresso, alla prima apertura utile; registrazione dell'uscita dalla rete, senza impiego della flotta di consegna nella prima versione.

Il criterio di consegna è cumulativo al momento dello scarico/accettazione. L'eventuale trattamento di un danno scoperto retroattivamente dopo l'accettazione richiede una regola specifica, non ancora concordata.

## 9. Recuperi e decisioni dell'operatore

Se i danni impediscono il raggiungimento delle quote, richiedere integrazione almeno fino al minimo di ciascun articolo deficitario. Non richiedere automaticamente il 100%. Esempio: richiesti 100 ricambi, minimo 90, consegnati 85 utilizzabili → almeno 5 da recuperare.

Il recupero e l'invio di un mezzo sostitutivo richiedono approvazione. Proposta con quantità mancanti, attività necessarie e stima di tempi/ritardo. Viaggi aggiuntivi associati alla stessa missione e scadenza originale invariata.

| Decisione | Effetto |
|---|---|
| Approva | Il recupero può proseguire |
| Rinvia | Richiesta aperta, tempo di attesa crescente |
| Rifiuta proposta | Missione bloccata in attesa di alternativa |
| Annulla esplicitamente missione | Stato annullato, motivazione e consegnato conservati |

Annullamento libera scorte/mezzi prenotati ma non impegnati. Carico in viaggio richiede una destinazione di scarico; non scompare. La scelta della destinazione è un dettaglio ancora aperto.

Modalità interattiva: decisione umana, attesa misurata nel tempo simulato. Modalità batch: approvazione simulata, di default senza rifiuti; rifiuti/annullamenti possono essere scenari specifici.

| Missione | Tempo di approvazione simulato |
|---|---:|
| Urgente | 5–15 minuti |
| Ordinaria | 15–60 minuti |

Estrazione in multipli di cinque minuti con seed. Il tempo effettivo futuro di risposta non è una feature disponibile prima della decisione.

## 10. Spazio, tempo e rete

- Area iniziale 100 × 100 km, dimensioni configurabili.
- 25 nodi: 5 depositi + 20 incroci.
- 40 collegamenti bidirezionali, con velocità di riferimento di 30, 50 o 70 km/h.
- Lunghezza derivata dalle coordinate. Attraversamento geometrico senza nodo non implica connessione.
- Ogni deposito raggiungibile; almeno due percorsi distinti fra ogni coppia di depositi.
- Rete generata con seed e validata prima delle missioni.
- Passo predefinito 5 minuti, configurabile e registrato.

Il percorso minimizza il tempo previsto usando le informazioni disponibili. Può essere ricalcolato quando cambiano le condizioni o una strada è impraticabile. Un mezzo già su un arco raggiunge il prossimo incrocio utile, senza teletrasporto.

Cambio di percorso se risparmio stimato almeno 5 minuti E almeno 10% del tempo residuo. I limiti non si applicano a un percorso impraticabile. Tracciare motivo, vecchio/nuovo percorso e nuova stima.

Traffico di fondo separato dalla congestione prodotta dalla flotta. La formula, le capacità degli archi e la gestione delle chiusure non sono ancora fissate. Una flotta di dieci mezzi potrebbe generare poca congestione su una rete ampia: verificarlo, senza forzare artificialmente il risultato.

Scadenze libere anche fra due tick: l'ordine degli eventi e la precisione sub-step vanno specificati prima di implementare gli esiti. Arrotondamenti numerici non devono produrre mancati completamenti artificiali.

## 11. Imprevisti: parametri approvati

### 11.1 Guasti meccanici

| Parametro | Regolare / sotto pressione | Perturbato |
|---|---:|---:|
| Probabilità per ora effettiva di marcia | 0,5% | 2% |
| Guasti riparabili sul posto | 80% | 80% |
| Riparazione sul posto | 15–60 minuti | 30–120 minuti |

Il mezzo riparabile attende e poi riprende. Non riparabile: approvazione del sostituto, arrivo dalla posizione reale simulata, trasferimento del carico (10 minuti di preparazione più movimentazione). Il sostituto rispetta compatibilità e capacità.

Ripristino del mezzo guasto: 24–48 ore dal guasto, comprensive di recupero/riparazione esterni. Rientro al deposito di origine del viaggio interrotto soltanto dopo che il carico è stato gestito. L'istante esatto se il carico resta bloccato oltre la finestra va definito. Un guasto meccanico non implica automaticamente danno alla merce o interruzione frigorifera.

### 11.2 Forniture esterne

| Parametro per fornitura | Regolare / sotto pressione | Perturbato |
|---|---:|---:|
| Probabilità di ritardo | 10% | 30% |
| Ritardo se presente | 1–6 ore | 4–24 ore |
| Probabilità di quantità incompleta | 5% | 15% |
| Quota ricevuta per articolo interessato | 80–95% | 60–90% |

Ritardo e incompletezza possono coesistere. Quantità intere. Selezione degli articoli coinvolti, direzione dell'arrotondamento e dipendenze fra eventi da precisare.

### 11.3 Danno da movimentazione

Probabilità per unità e per operazione di carico/scarico:

| Categoria | Regolare / sotto pressione | Perturbato |
|---|---:|---:|
| Alimenti non refrigerati | 0,2% | 0,6% |
| Refrigerati | 0,3% | 0,9% |
| Materiale sanitario | 0,3% | 0,9% |
| Ricambi | 0,1% | 0,3% |
| Elettronica | 0,5% | 1,5% |

Applicare solo alle unità movimentate. Scarico parziale non riespone quelle rimaste sul mezzo. Trasferimento al sostituto comprende scarico e carico. Una unità inutilizzabile non viene persa una seconda volta. Il danno non visibile emerge all'ispezione. Eventuali ulteriori danni da viaggio non sono parametrizzati: non duplicare implicitamente questo rischio.

### 11.4 Refrigerazione

| Parametro | Regolare / sotto pressione | Perturbato |
|---|---:|---:|
| Interruzione per ora di funzionamento dell'impianto | 0,2% | 1% |
| Durata | 15–60 minuti | 30–120 minuti |
| Tolleranza cumulativa iniziale | 60 minuti | 60 minuti |

Probabilità applicata all'impianto, anche durante le soste, non a ciascun collo. Merce presente esposta alla stessa interruzione. Tempo cumulativo non azzerato al ripristino; superamento della tolleranza rende inutilizzabili le unità interessate nello stato interno. Allarme osservabile subito, quantità utilizzabile confermata dall'ispezione. Serve tracciamento per lotto/unità o gruppi con storia di esposizione omogenea, non un contatore globale per articolo.

La tolleranza è un parametro artificiale del simulatore, non una regola per prodotti reali. Applicazione dettagliata agli impianti dei depositi e danni successivi alla consegna da formalizzare.

### 11.5 Traffico e meteo

| Parametro | Regolare / sotto pressione | Perturbato |
|---|---:|---:|
| Moltiplicatore tempo per traffico di fondo | 1,0–1,4 | 1,2–2,0 |
| Moltiplicatore meteo avverso | 1,1–1,3 | 1,2–1,5 |
| Durata episodio meteo | 1–3 ore | 2–6 ore |
| Avvio episodio per ora senza episodio attivo | 5% | 15% |
| Aggiornamento traffico | 30 minuti | 30 minuti |
| Aggiornamento previsione meteo | 60 minuti | 60 minuti |
| Orizzonte previsione meteo | 6 ore | 6 ore |

Moltiplicatori combinati: 30 minuti × 1,2 × 1,1 = 39,6 minuti prima della congestione della flotta. Meteo su tutta la mappa, episodi non sovrapposti; traffico per gruppi di strade. Condizioni persistenti, non rumore indipendente per mezzo/tick. Previsioni meteo imperfette e versionate; la loro costruzione non può rivelare la sequenza futura vera al modello.

Le probabilità orarie devono essere convertite coerentemente al passo. Le distribuzioni all'interno degli intervalli, quando non esplicitamente approvate, restano scelte implementative da documentare; non assumere tacitamente uniformità ovunque.

## 12. Generazione degli scenari

### 12.1 Orizzonte e profili

Generazione di nuove missioni per 7 giorni; prosecuzione fino a 7 ulteriori giorni, limite totale 14 giorni simulati. Durate configurabili. Arresto anticipato quando tutte le missioni e operazioni collegate sono finite. Forniture, prelievi e recuperi continuano nel periodo aggiuntivo; chiarire il criterio di arresto rispetto alle attività di fondo ancora attive.

| Profilo | Missioni medie/giorno, intera rete | Missioni medie nella settimana |
|---|---:|---:|
| Regolare | 10 | 70 |
| Sotto pressione | 20 | 140 |
| Perturbato | 10 | 70 |

Conteggi di nuove richieste indipendenti, non viaggi integrativi o forniture esterne. Arrivi variabili e riproducibili. Il profilo sotto pressione modifica inizialmente la frequenza delle missioni mantenendo condizioni esterne regolari. Il perturbato modifica imprevisti mantenendo domanda regolare. Combinazioni sono estensioni sperimentali, non garanzia di esiti.

### 12.2 Composizione

- 20% di missioni urgenti in ogni profilo.
- 1–5 categorie compatibili; 1–3 articoli per categoria selezionata.
- Quantità per articolo presente: piccoli 20–100, medi 10–50, grandi 5–25 unità.
- Estrazione uniforme intera delle quantità; stessi intervalli nei tre profili.
- Carichi per uno o più mezzi; non ridurre la richiesta per nascondere carenze di stock.
- Consentiti tutti i tipi di coppia di depositi, senza obbligo di collegamento stradale diretto.
- Distribuzione delle coppie, scelta categorie/formati e orari di generazione da completare.

### 12.3 Scadenze automatiche

Durata stimata iniziale costruita con informazioni disponibili alla creazione: scorte/arrivi previsti, mezzi, code, calendari, carico, viaggio, scarico. La durata effettiva futura non deve influenzarla.

| Tipo | Moltiplicatore della durata stimata | Frequenza iniziale |
|---|---:|---:|
| Stretta | 1,0–1,2 | 30% |
| Ordinaria | 1,3–1,6 | 50% |
| Ampia | 1,8–2,2 | 20% |

Scadenza = avvio programmato + durata stimata × margine. Tipologia indipendente dall'urgenza; distribuzione comune ai profili. Richieste manuali mantengono scadenza libera. Definire come gestire una stima iniziale non finita o indisponibile.

Non imporre un rapporto 50/50 fra ritardi e puntualità: gli esiti emergono dalle dinamiche. Documentare frequenze osservate e carenza di esempi nelle categorie di interesse.

## 13. Previsioni e informazioni utilizzabili

### 13.1 Due momenti distinti

Modelli/pipeline separati, versionati e valutati per:

1. Prima dell'avvio: piano e stato noto prima delle attese operative.
2. Durante la missione: piano più avanzamento ed eventi già osservati, incluse attese prima della partenza.

Prima della scadenza produrre probabilità di mancato raggiungimento di almeno una quota e stima del ritardo condizionata al fatto che la missione sia tardiva. Esempio di presentazione: «35% di probabilità di ritardo; se tardiva, stima 40 minuti». La stima condizionale non è il ritardo atteso su tutte le missioni.

Dopo la scadenza, se non sono raggiunte le quote, mostrare ritardo accumulato e tempo residuo stimato, non una probabilità di un fatto già accaduto. Ritardo finale previsto deve essere coerente con accumulato + residuo. Il modello o metodo specifico per il residuo va definito.

### 13.2 Frequenza

Previsione iniziale prima dell'avvio. Aggiornamenti ogni 30 minuti simulati, configurabili, e al passo di eventi osservati rilevanti: partenza, guasto, variazione percorso, scarico, approvazione e variazioni di disponibilità pertinenti. Controllo obbligatorio alla scadenza; dopo raggiungimento quote registrare esito e cessare previsioni dell'obiettivo.

Più eventi nello stesso passo → una previsione dopo la loro elaborazione osservabile. Ogni previsione conservata con istante, versione e snapshot ricostruibile. Interruzione delle previsioni a stato annullato è una conseguenza del distinto ciclo di vita, da codificare nei contratti.

### 13.3 Feature e anti-leakage

Feature iniziali: quantità/soglie, peso/volume, scadenza e margine, urgenza, compatibilità, scorte disponibili/riservate, forniture previste, mezzi e trasferimenti, banchine/code, calendari, rete/tempo previsto, traffico e previsioni meteo note.

Feature durante la missione: stato, tempi trascorsi, carichi e consegne osservate per articolo, deficit residui, posizione/avanzamento, eventi rilevati, approvazioni e attese note.

Nessun accesso a stato nascosto, danno non ispezionato, durata futura di guasto/approvazione, arrivo effettivo futuro, meteo vero futuro, consegnato finale o tempo di completamento finale. Tenere separato il registro interno usato per il ground truth. L'ETL delle feature deve applicare il cutoff di osservabilità, non solo il timestamp fisico dell'evento.

### 13.4 Incertezza, spiegazione e astensione

Intervalli con copertura obiettivo dell'80% per il ritardo condizionale e per le stime residue pertinenti. Valutare copertura e ampiezza; non presentare l'80% come garanzia già dimostrata. Spiegazioni dei fattori associati alla stima, senza attribuire causalità non verificata.

| Condizione | Risposta |
|---|---|
| Dati completi, scenario rappresentato | Previsione, intervallo, spiegazione |
| Dati opzionali mancanti | Previsione se gestibili, elenco delle mancanze |
| Dati obbligatori mancanti/incoerenti | Astensione con motivo |
| Scenario fuori ambito validato | Avviso; eventuale baseline distinta, senza presentarla come stima ML validata |

Misurare anche la quota di richieste coperte dalle previsioni, evitando che le astensioni nascondano casi difficili. L'assenza di un allarme fuori distribuzione non dimostra automaticamente affidabilità.

## 14. Dataset, split e valutazione

### 14.1 Lotto iniziale

| Profilo | Simulazioni | Missioni attese |
|---|---:|---:|
| Regolare | 30 | Circa 2.100 |
| Sotto pressione | 30 | Circa 4.200 |
| Perturbato | 30 | Circa 2.100 |
| Totale | 90 | Circa 8.400 |

Prima del lotto: pilota per correttezza, tempi, varietà degli esiti e sostenibilità delle code. Snapshot multipli non sono missioni indipendenti. Volumi attesi non garantiti; ampliare solo se evidenza insufficiente.

### 14.2 Split approvato

| Insieme | Quota | Simulazioni | Per profilo |
|---|---:|---:|---:|
| Training | 60% | 54 | 18 |
| Calibrazione | 20% | 18 | 6 |
| Test finale | 20% | 18 | 6 |

Tuning tramite validazione interna al training raggruppata per simulazione. Tutte le missioni/snapshot di una simulazione restano insieme; anche varianti dello stesso scenario casuale di base non devono attraversare gli insiemi. Se raggruppamenti più ampi rendono impossibili i conteggi esatti, documentare il criterio prima delle estrazioni.

Test finale non usato per scegliere modello, parametri o soglie. Se consultato per modificare il sistema, un nuovo test indipendente è necessario per una nuova verifica conclusiva. Calibrazione degli intervalli/probabilità da definire senza riutilizzare il test.

### 14.3 Baseline e confronto

Confrontare una stima semplice basata su tempi previsti di attesa, movimentazione, viaggio e scarico con modelli semplici e più flessibili. Nessun champion deciso a priori. Logistic Regression/XGBoost restano candidati storici per la classificazione; regressori, intervalli e metodi specifici non sono ancora scelti.

Classificazione: capacità discriminante e calibrazione (AUC/PR-AUC, Brier/ECE previste nei documenti originali). Durata: errore assoluto in minuti e casi di errore elevato. Intervalli: copertura effettiva e ampiezza. Nessun obiettivo arbitrario di «90% accuracy».

Report separati prima dell'avvio, alla partenza e nelle fasi successive; per aggiornamenti, stesso peso complessivo a ogni missione. Segmenti per profilo, urgenza e presenza di refrigerato, sempre con numerosità e avvisi per gruppi piccoli. Considerare dipendenza fra missioni della stessa simulazione nell'incertezza delle metriche.

Dati annullati/censurati mantenuti nel registro; l'inclusione nella regressione richiede una regola esplicita. Escluderli silenziosamente potrebbe sottorappresentare i ritardi più lunghi.

### 14.4 Interventi e aggiornamento modello

Il modello informa e non modifica le decisioni automaticamente. Registrare interventi e distinguere esperimenti automatici da sessioni interattive. Un allarme seguito da intervento efficace non è automaticamente un falso allarme.

Training candidato, confronto con versione attuale sugli stessi dati di valutazione, report, approvazione manuale alla sostituzione. Conservare modello, configurazione, dati di riferimento, report e possibilità di rollback. Peggioramento → avviso; nessuna promozione automatica. Gestire nuovi cicli con dati di valutazione adeguati, senza usare ripetutamente il test finale come strumento di tuning.

## 15. Contratti dati e qualità

### 15.1 Entità approvate

| Entità | Contenuto |
|---|---|
| Simulazioni | Configurazione, seed, profilo, versione simulatore |
| Missioni e righe articolo | Origine/destinazione, quantità, soglie, urgenza, avvio/scadenza |
| Viaggi e carichi | Mezzo, percorso, quantità effettive e trasferimenti |
| Movimenti magazzino | Ingressi/uscite, riserve, riassegnazioni, quarantena e rimozioni |
| Eventi | Guasti, tempi, stati, richieste e decisioni |
| Previsioni | Istante, informazioni usate, versioni, risultati e astensioni |
| Esiti | Quote, puntualità, ritardo o osservazione incompleta |

Formalizzazione proposta: identificativi `simulation_id`, `mission_id`, `mission_line_id`, `item_id`, `trip_id`, `vehicle_id`, `depot_id`, `event_id`, `prediction_id`. Per esposizione e danni aggiungere tracciamento di lotti/gruppi fisici; non è sufficiente il solo codice articolo.

Ogni record richiede versione schema e collegamenti verificabili. Conservare timestamp UTC e tempo simulato; calendario locale esplicito. Gli eventi distinguono istante fisico e istante di osservabilità. Tipi, nullabilità, vincoli, idempotenza, chiavi e migrazioni vanno completati come contratti eseguibili.

La pipeline originale CSV/eventi → Silver validato → Gold per ML rimane un riferimento compatibile, ma il Gold deve avere granularità missione e, per rolling, missione/istante. I nomi e formati finali sono da fissare; le strutture per convoglio non bastano.

### 15.2 Gestione errori

| Errore | Azione approvata |
|---|---|
| Input manuale invalido | Rifiuto con campo/motivo |
| Riga importata malformata | Quarantena dati e report |
| Scorte negative, duplicazioni, assegnazioni incompatibili | Arresto simulazione e stato non valido |
| Informazioni future in feature | Blocco costruzione dataset ML |

Simulazioni non valide escluse dal training ma conservate con seed, configurazione e diagnosi. Importazione bloccata oltre lo 0,5% di righe invalide; sotto soglia procedere solo mantenendo integrità delle relazioni. Al valore esatto di soglia applicare il criterio «oltre» dei documenti originali. Anche una sola violazione critica può bloccare indipendentemente dalla percentuale.

La quarantena dei record non va confusa con quella fisica delle merci.

## 16. Dashboard e modalità d'uso

| Vista | Contenuti |
|---|---|
| Missioni e previsioni | Quote per articolo, stati, scadenze, probabilità, minuti stimati/effettivi, storico, richieste di approvazione |
| Depositi e scorte | Disponibile/riservato/in arrivo, arretrati, occupazione, banchine e quarantena |
| Flotta e rete | Posizioni, stati, carichi, percorsi, guasti, viaggi a vuoto |
| Analisi e qualità modello | Tempi per fase, puntualità, utilizzo, colli di bottiglia, errori, calibrazione, intervalli, baseline |

Le spiegazioni devono essere leggibili e distinguere dati osservati da stime. Mostrare ultimo aggiornamento e astensione. La dashboard non deve esporre lo stato nascosto del simulatore come informazione operativa; una vista diagnostica separata può essere usata per il controllo sperimentale, se realizzata.

## 17. Locale e demo online

Prima versione locale riproducibile, poi demo online al completamento. Nessuna pubblicazione eseguita da questo documento.

| Accesso online | Funzioni |
|---|---|
| Visitatore | Consultazione libera di scenari completati e risultati |
| Sessione dimostrativa | Scenario predefinito, decisioni manuali, aggiornamento previsioni |
| Amministratore | Configurazioni, dataset, training e approvazione modelli |

Sessioni dimostrative separate per dati e decisioni, limiti di risorse e durata. Nessun training o modifica del catalogo condiviso per visitatori. Versione locale con funzioni complete di sperimentazione. Autenticazione amministrativa, implementazione isolamento, limiti numerici, retention, hosting e costi sono da definire prima del rilascio online.

La specifica originaria indicava FastAPI, React/Next.js, Azure, Postgres, MLflow e DVC; il prototipo esaminato usava FastAPI e Streamlit. La conversazione non ha scelto definitivamente lo stack della nuova UI o il provider di hosting: non imporre una migrazione non approvata.

## 18. Criteri di completamento della prima versione

| Area | Evidenza richiesta |
|---|---|
| Simulatore | Riproducibilità, conservazione quantità, capacità rispettate, nessuna doppia assegnazione |
| Dati | Contratti validati, eventi ricostruibili, assenza leakage verificata |
| Previsioni | Pipeline iniziale/rolling, baseline e report su test indipendente |
| Incertezza | Copertura/ampiezza intervalli e frequenza astensioni misurate |
| Interfaccia | Quattro viste e flussi di approvazione verificati |
| Qualità software | Test significativi dei casi critici, controlli automatici, copertura ≥90% del nucleo simulatore–dati–ML |
| Consegna | Avvio locale documentato, demo online, esempi, risultati e limiti |

La copertura numerica non sostituisce la verifica delle regole. Se un modello complesso non migliora la baseline, riportarlo e adottare il metodo meglio supportato. Il completamento del portfolio non equivale a certificazione di uso reale.

I precedenti SLO (p95 <600 ms, p99 <1 s, uptime 99,5%, avvio job entro 1 minuto) rimangono obiettivi storici da riesaminare su hardware, carico e ambiente definiti. Non sono risultati misurati né SLA contrattuali della demo. Distinguere il costo della previsione da simulazione e spiegazione locale.

## 19. Stato del lavoro già esaminato

La revisione precedente ha esaminato `Zistax/digital-twin-military-logistics`, branch master, commit `c477ade4ed05c9f0fec7e72cc9279732fa8c84e4`. Questo documento usa quella fotografia; non attesta una nuova verifica remota del repository.

Presenti nel prototipo: simulatore minimale, CSV, dataset/training Logistic Regression, FastAPI, Streamlit, configurazioni e test. Non confondere i documenti delle fasi future con codice implementato.

Problemi riprodotti nella revisione:

- Dataset da 18 righe/4 simulazioni; tutti i dieci esempi di classe negativa rispetto al completamento avevano feature di durata/timestep a zero, ricavate dai log finali.
- Split per riga con tre simulazioni condivise fra training e test; report al 100% su soli sei esempi non probante.
- Caso 60 minuti / passo 10: zero completati su tre per confronto numerico del progresso. Caso 125/10 terminato a 120 minuti.
- Nomi CSV al secondo con collisione fra esecuzioni e rischio di rilettura di dati altrui.
- 16 test passati nell'ambiente di revisione, coverage 56%, soglia configurata a zero; Ruff con 36 violazioni di lunghezza; Black non selezionava file per configurazione errata.

Non sono stati corretti nel corso del consolidamento. I test storici non provano la nuova specifica. I risultati ML del prototipo non vanno usati come baseline validata del nuovo progetto.

## 20. Regole originali sostituite o riclassificate

| Tema | Specifica 2025 | Decisione 2026 |
|---|---|---|
| Finalità | Prodotto completo operativo | Portfolio solido, poi validazione reale |
| Target | `failure` generico, severità separata | Ritardo rispetto a quote per articolo; minuti condizionali e residui |
| Missioni | Chiave sessione/convoglio, mission_id opzionale | Missione identificata, righe articolo, molti viaggi/snapshot |
| Scadenze | 2/4/6 ore per High/Medium/Low | Libere, separate dall'urgenza ordinaria/urgente |
| Timeout | Park & Resume, nuova missione | Prosecuzione oltre scadenza, recuperi sulla stessa missione |
| Priorità | Tre livelli e preemption deposito | Urgente/ordinaria, nessuna interruzione delle operazioni |
| Mezzi | Tipi militari generici | Quattro furgoni, quattro standard, due refrigerati |
| Rischio/eventi | Attack, escort e costi di rischio | Guasti, forniture, danni, refrigerazione, traffico/meteo del perimetro sintetico |
| Routing | Tempo + rischio + congestione, guardrail RL | Minor tempo previsto, rerouting con soglie approvate |
| Depositi | Due banchine generiche e rifornimenti fissi | Cinque strutture, capacità/calendari/catalogo e rifornimenti configurabili |
| Dataset | 500 campioni/ciclo e bilanciamento 50/50 | 90 simulazioni, circa 8.400 missioni, frequenze d'esito emergenti |
| Split | Holdout 20% + cinque fold genericamente descritti | 60/20/20 per gruppi; tuning interno al training |
| Modello | XGBoost champion a priori | Baseline e candidati scelti da validazione; iniziale e rolling separati |
| Soglie classificatore | High 0,60 / Medium 0,70 / Low 0,80 | Non trasferite al nuovo target; quote merce sono una cosa diversa |
| RL e /optimize | Parte del prodotto iniziale | Fase 2; prima versione informativa |
| Qualità | Coverage ≥90% generica | ≥90% del nucleo simulatore–dati–ML e casi critici |
| Accessi | Planner/Analyst/Admin/Viewer multi-tenant | Demo con visitatore, sessione isolata e amministratore |
| Cloud/retention | Azure avanzato e preset tenant | Requisiti operativi della demo da completare; non tutti obbligatori v1 |

Rimangono compatibili come principi: dati sintetici senza PII, timestamp UTC, versionamento, audit, controllo qualità, configurazioni riproducibili, documentazione di limiti. Apache-2.0 è la licenza del core nel repository esaminato; questa specifica non la modifica. Connettori proprietari, i18n IT/EN, SSO, ETL ogni 60 minuti/backfill 24 ore, trigger PSI/AUC/Brier e supply-chain avanzata sono proposte storiche da confermare/prioritizzare, non funzionalità dichiarate completate.

## 21. Piano di sviluppo con consegne verificabili

Tutte le attività seguenti sono da realizzare/verificare sul nuovo perimetro. Nessuna spunta implica lavoro già svolto.

| ID | Attività | Dipendenze | Criterio di uscita |
|---|---|---|---|
| F01 | Congelare requisiti e registro decisioni, risolvere punti P01–P04 | Questa specifica | Regole temporali, target e stati non ambigui |
| F02 | Correggere regressioni prototipo e configurazione qualità | F01 | Casi 60/10 e 125/10 gestiti; output univoci; lint/format realmente eseguiti |
| F03 | Contratti schema, configurazioni e identificativi | F01 | Validazione input, relazioni, unità, migrazioni e cutoff definiti |
| S01 | Catalogo, missioni e calcolo quote/esiti | F03 | Quote ceil per articolo; puntualità al limite; nessuna compensazione fra formati |
| S02 | Depositi, calendari, stock, riserve e banchine | S01 | Capacità e quantità conservate, orari/preemption rispettati |
| S03 | Flotta, viaggi e rete | S01–S02 | Assegnazioni esclusive, multi-mezzo, trasferimenti a vuoto e routing riproducibili |
| S04 | Forniture, prelievi, arretrati e riordino | S02–S03 | Nessun ordine/domanda duplicati; scarico parziale e riapertura corretti |
| S05 | Guasti, danni, freddo, recuperi e quarantena | S03–S04 | Tracciamento fisico/observabile, approvazioni e conservazione quantità |
| S06 | Generatore dei tre profili e arresto esperimenti | S01–S05 | Riproducibilità con seed; casi aperti censurati correttamente |
| D01 | Eventi/trace, dataset validati e KPI | F03 + S06 | Ricostruzione stati e feature senza futuro |
| D02 | Pilota e revisione documentata parametri | D01 | Tempi praticabili, varietà esiti e assenza di errori/infinite attese non spiegate |
| D03 | Lotto 90 simulazioni e split | D02 | Manifesti di gruppi/seed, distribuzioni e integrità verificate |
| M01 | Baseline e previsione iniziale | D03 | Confronti interni al training, probabilità/durata/astensione |
| M02 | Rolling, residuo e intervalli | M01 | Aggiornamenti coerenti, intervalli calibrati e peso per missione |
| M03 | Test finale, report e registro modelli | M02 | Report indipendente, limiti, promozione manuale e rollback |
| U01 | API e quattro viste | F03; integrazione S06/M02 | Flussi missione/approvazione e separazione stato nascosto funzionanti |
| R01 | Pacchetto locale riproducibile | S06–M03 + U01 | Istruzioni e demo end-to-end ripetibili |
| R02 | Demo online limitata | R01 | Accessi/isolamento/limiti verificati; pubblicazione come azione separata |

Prima implementazione consigliata: F01 → F03/S01 con una missione deterministica semplice come caso di riferimento, poi estensioni progressive. Non tentare tutte le dinamiche contemporaneamente. Il perimetro completo rimane quello approvato.

## 22. Verifiche di accettazione mirate

| Caso | Risultato atteso |
|---|---|
| Articolo richiesto in 5 unità con soglia 90% | Minimo 5, non 4 |
| Articolo A sopra quota e B sotto | Missione non raggiunge l'obiettivo |
| Ultima quota alle 14:35, scadenza 14:00 | Ritardo 35 minuti anche se altri articoli erano puntuali |
| Ultima quota esattamente alla scadenza | Puntuale, nessun errore di arrotondamento |
| Quote raggiunte ma carico extra ancora in viaggio | Obiettivo concluso; viaggi/mezzi restano impegnati |
| Ordinaria con stock parziale | Attende; urgente può partire solo con tutti i minimi |
| Riassegnazione scorte a urgente | Quantità conservate, carico iniziato protetto, scadenza ordinaria immutata |
| Arrivo a deposito chiuso | Attesa registrata; operazione già iniziata finisce oltre chiusura |
| Scarico parziale | Solo quantità scaricate entrano nello stock; banchina liberata; mezzo occupato |
| Guasto e sostituzione | Attesa approvazione/arrivo/trasferimento distinte, nessuna duplicazione del carico |
| Due interruzioni frigorifere | Esposizione cumulativa, non reset; danni fisici distinti da osservazione |
| Quarantena piena | Residuo sul mezzo, nessun superamento occulto capacità |
| Import con poche righe ma relazione critica persa | Blocco/invalidatione anche sotto soglia percentuale |
| Cambia solo un dato futuro nascosto | Feature e previsione a t_pred restano invariate |
| Fine simulazione prima del completamento | Nessun ritardo finale artificiale |
| Stesso seed/versioni/configurazione | Stessi eventi ed esiti secondo il contratto di determinismo |
| Cambia il passo temporale | Frequenze eventi coerenti; nessun confronto esatto fragile del progresso |
| Due sessioni contemporanee | Identità/output distinti e nessuna contaminazione |

Questi test verificano comportamento e integrità; evitare test che riproducono soltanto le stesse formule del codice senza casi di confine o proprietà osservabili.

## 23. Registro dei dettagli ancora aperti

Il perimetro funzionale è approvato, ma la specifica non pretende di essere già un insieme completo di contratti eseguibili. I punti seguenti devono essere chiusi prima delle attività indicate, senza trasformare silenziosamente ipotesi in decisioni dell'utente.

| ID | Dettaglio da completare | Prima di |
|---|---|---|
| P01 | Ordine degli eventi simultanei, timestamp sub-step, scadenze fra tick, avanzamento lungo più archi nello stesso passo | S01/S03 |
| P02 | Stati separati di obiettivo, viaggio e chiusura logistica; danno scoperto dopo accettazione; definizione di D_i(t) | S01/S05 |
| P03 | Trattamento annullamenti e osservazioni censurate nel training/regressione; bias da soli completati | D03/M01 |
| P04 | Identità lotti/gruppi fisici per danni, trasferimenti, prenotazioni ed esposizione frigorifera cumulativa | F03/S05 |
| P05 | Quantificazione capacità archi/congestione, traffico autocorrelato, chiusure e disposizione nodi; definizione precisa dei due percorsi | S03 |
| P06 | Algoritmo meteo forecast imperfetto, errori/correlazioni e intervalli di validità senza accesso futuro | S06/M01 |
| P07 | Distribuzioni non approvate negli intervalli, conversione probabilità, correlazioni eventi, selezione articoli forniture parziali | S05–S06 |
| P08 | Assegnazione/packing deterministico, simultaneità partenze multi-mezzo, sostituzione quando serve più di un mezzo, tempi di ritorno riparato | S03/S05 |
| P09 | Area d'attesa e occupazione dei fornitori esterni durante scarico; ordine di selezione merci con spazio limitato | S02/S04 |
| P10 | Formula posizione inventariale e ricezioni entro lead time, saturazione, capacità del riordino, distribuzione stock se non entra, casi domanda zero | S04 |
| P11 | Generatore coppie/categorie/formati/orari e prelievi nei giorni chiusi; scorte comuni e domanda sotto pressione | S06 |
| P12 | Estimatore iniziale ETA con calendari e più mezzi; scadenza quando stima indisponibile | S06 |
| P13 | Arresto in presenza di richieste locali/forniture di fondo; mantenimento calendario e ordinazioni nel proseguimento | S06 |
| P14 | Modelli specifici, target puntuale media/mediana, stima residua, calibrazione intervalli, campionamento/pesi snapshot, soglie di astensione | M01–M02 |
| P15 | Soglie quantitative di promozione dopo il pilota, incertezza metriche per simulazione e numerosità minima per segmenti | M03 |
| P16 | Schema completo, tipi, unità, nullabilità, deduplica, replay, versioni e migrazioni; versioni catalogo e feature | F03/D01 |
| P17 | Stack finale database/UI, API asincrone, cancellazione/idempotenza job, persistenza e versionamento artefatti | U01/R01 |
| P18 | Autenticazione amministratore, isolamento sessioni, quote/calcolo, durata sessione, retention, hosting/costi e obiettivi prestazionali misurabili | R02 |
| P19 | Pausa/accelerazione interattiva e misurazione dell'attesa umana; destinazione del carico annullato | U01/S05 |
| P20 | Danni di viaggio ulteriori alla movimentazione e guasti frigoriferi nei depositi: confermare la loro modellazione evitando nuovi rischi impliciti | S05 |

Sono decisioni tecniche delimitate, non invito ad ampliare il prodotto. Se una soluzione cambia una regola approvata, evidenziarla come modifica di specifica prima di adottarla.

## 24. Istruzioni per chi implementa

1. Usare questa specifica e il registro dei punti aperti come riferimento; non recuperare automaticamente dal design 2025 regole sostituite.
2. Prima di modificare il repository, verificare stato corrente, istruzioni locali e differenze dal commit esaminato.
3. Preservare licenza, documentazione utile e codice riutilizzabile; il vecchio modello/dataset non è validato per il nuovo target.
4. Implementare per tappe, con dati piccoli e controllabili prima del lotto completo.
5. Distinguere configurazioni approvate, proposte tecniche e valori modificati dopo il pilota.
6. Trattare validazione temporale, conservazione quantità e identità dei viaggi come requisiti centrali, non controlli opzionali finali.
7. Non dichiarare il modello affidabile o pronto per uso reale sulla base dei soli risultati sintetici.
8. Pubblicazione della demo, promozione del modello e azioni operative hanno percorsi distinti; questo consolidamento non ne costituisce esecuzione.

**Stato alla consegna del documento:** progettazione funzionale consolidata; parametri approvati raccolti; differenze storiche e backlog identificati; implementazione del nuovo perimetro non ancora eseguita.
