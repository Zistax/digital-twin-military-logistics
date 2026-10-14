# S06 — generazione degli scenari

13 ottobre 2026. Implementati catalogo, domanda, inizializzazione,
condizioni ambientali e forniture stocastiche. Il perimetro funzionale S06 è integrato e verificato con prove brevi end-to-end.

## Implementato

- Catalogo dei 15 articoli con pesi, volumi, movimentazione e quote della specifica.
- Cinque depositi, capacità ordinarie/refrigerate e quarantene, banchine condivise
  e calendari settimanali Europe/Rome della specifica.
- Dieci mezzi: quattro furgoni, quattro standard, due refrigerati. Ogni centrale
  ha un mezzo di ciascun tipo. Locale A ha un furgone e uno standard, Locale B
  un furgone, Locale C uno standard: scelta iniziale esplicita e riproducibile.
- Rete con seed: 25 nodi, 40 strade, percorsi alternativi.
- Arrivi Poisson omogenei su tutte le 24 ore, con media 10 richieste/giorno
  regolare e perturbato, 20 sotto pressione. I conteggi non sono imposti.
- Coppie dirette uniformi fra depositi distinti; numero di categorie uniforme
  fra 1 e quelle compatibili; sottoinsieme uniforme; da 1 a 3 formati per
  categoria con selezione uniforme. Quantità intere negli intervalli concordati.
- Urgenza Bernoulli al 20%, indipendente da composizione e tipo di scadenza.
- Tipi di scadenza 30/50/20%; margini estratti in centesimi negli intervalli
  concordati. Sono margini pianificati, non scadenze già calcolate.
- Flussi casuali separati per arrivi, coppie, composizione, quantità, urgenza
  e margini. Regolare e perturbato condividono le richieste a parità di seed.
  Sotto pressione cambia il tempo degli arrivi, mantenendo la stessa sequenza
  delle altre caratteristiche. Le varianti dello stesso seed dovranno restare
  nello stesso insieme train/calibration/test.
- Domanda media di spedizione calcolata analiticamente dai parametri, senza
  leggere le richieste future estratte. Il consumo locale atteso include
  l'arrotondamento per eccesso, non solo il 20% medio prima di arrotondare.
- Scorte iniziali comuni ai tre profili: tre giorni ai centrali, uno ai locali,
  con rispetto delle capacità e registro delle eventuali limitazioni.
- Prelievi locali programmati per tutto l'orizzonte; regole di riordino con
  soglie/obiettivi e tempi di fornitura della specifica.

`initialize_scenario(config)` restituisce il motore e il registro iniziale.
`generate_requests(config)` restituisce richieste immutabili. Il motore non
riceve automaticamente tutte le missioni future: saranno inserite al loro
istante di creazione dal runner, dopo la stima osservabile della durata.

## Stato

Perimetro funzionale S06 integrato, con limiti dello stimatore dichiarati sotto.
Il runner esegue richieste, ambiente, forniture, recuperi e arresto. La validazione
statistica su 7+7 giorni e il lotto da 90 simulazioni non sono stati eseguiti.

## Ambiente e forniture: integrazione del 13 ottobre

`EnvironmentWarehouse` applica condizioni a tutti gli archi prima della gestione
degli eventi e delle nuove partenze. Un arco già percorso mantiene il tempo
fissato all'ingresso, come previsto dal motore stradale.

Il gruppo di una strada dipende dal quadrante del suo punto medio nella mappa
100×100 km. Ogni 30 minuti il traffico viene aggiornato con 75% del valore
precedente e 25% di un'estrazione uniforme nell'intervallo del profilo. Questa
è una scelta sintetica esplicita per ottenere persistenza, non una calibrazione.

Ogni ora senza episodio attivo può iniziare un episodio meteo (5% regolare e
pressione, 15% perturbato). Durata uniforme in ore intere negli intervalli 1–3
o 2–6 ore; intensità uniforme negli intervalli concordati. Gli episodi non si
sovrappongono. Tutti gli archi condividono lo stesso meteo.

Il forecast `persistence-noise-v1` è emesso ogni ora con sei intervalli orari:
la componente avversa osservata decade di un fattore 0,65 per ora, con errore
uniforme crescente e valori limitati fra 1 e il massimo del profilo. Usa solo
meteo corrente e un proprio flusso casuale; non legge fine episodio o futuro
vero. Non è un modello meteorologico calibrato. Versioni e osservazioni restano
nel registro ambientale; `observed_environment()` restituisce copie della
vista corrente. La costruzione delle feature storiche rimane compito di D01.

Il riordino automatico applica adesso gli stessi ritardi e incompletezze del
comando di fornitura stocastica quando la policy è automatica. La modalità
deterministica mantiene arrivi puntuali e completi. `observed_supplies()` non
espone tempo e quantità effettivi prima dell'arrivo; gli snapshot diagnostici
continuano invece a contenere stato interno e non sono feature ML.

Il runner è descritto sotto; le prove end-to-end brevi non sostituiscono il pilota statistico.

## Stima osservabile iniziale

`estimate_request` produce una durata e un codice di metodo, oppure un motivo
esplicito di indisponibilità. Deve essere chiamato esattamente all'istante della
richiesta, dopo l'avanzamento del motore. Non modifica stato né flussi casuali.

Il metodo `observable-free-fleet-v1` usa stock disponibile, promesse future dei
fornitori, flotta libera e compatibile, trasferimenti a vuoto, capacità, code di
movimentazione, banchine, calendari e condizioni stradali correnti. Pianifica
l'intera quantità richiesta, anche per urgenze. Le operazioni avviate possono
terminare dopo la chiusura; la partenza aspetta tutti i carichi previsti.

`mission_from_estimate` applica il margine e arrotonda per eccesso al secondo.
Rifiuta stime indisponibili o riferite a un altro istante: non assegna scadenze
arbitrarie e non modifica l'inizio della richiesta.

Limiti dichiarati: è una prima euristica, non una simulazione predittiva delle
code. Non prevede il rilascio dei mezzi occupati, l'evoluzione del traffico,
futuri ordini di riapprovvigionamento o il consumo competitivo delle promesse
condivise. La gestione nel runner di una stima indisponibile usa una convenzione esplicita
di pianificazione, descritta sotto. Cinque test
verificano calendario, condizioni correnti, margini, assenza di modifiche allo
stato, invariabilità rispetto agli arrivi effettivi nascosti e indisponibilità.

## Runner e arresto — integrazione completata

`run_experiment` inserisce le richieste al loro istante, senza rivelare le
successive al motore. Dopo la generazione continua per il periodo aggiuntivo,
fino al limite configurato (default 7+7 giorni). I controlli di completamento
sono orari e configurabili; gli eventi interni mantengono i loro tempi esatti.
Non si arresta prima della fine del periodo di generazione.

Quando una stima è indisponibile, `RunPolicy.unavailable_allowance_s` fornisce
un budget sintetico di pianificazione (default 86.400 secondi), moltiplicato
per il margine già estratto. Restano immutati avvio, richiesta e urgenza. Il
registro conserva stima nulla, motivo di indisponibilità, base della scadenza
e `deadline_source=configured_allowance`. Non è una stima del modello e i
risultati dovranno essere segmentati per questa origine della scadenza nel
pilota. Il valore è una convenzione sperimentale modificabile, non calibrata.

L'arresto anticipato richiede completamento logistico di tutte le missioni e
assenza di viaggi, trasferimenti a vuoto, code interne, recuperi e riparazioni
meccaniche aperte. Forniture e prelievi continuano finché la simulazione avanza,
ma le sole attività di fondo, quarantene e allarmi frigoriferi non impediscono
l'arresto quando le missioni sono concluse. Questo evita un orizzonte infinito
causato dal riordino periodico.

Al limite temporale gli eventi dovuti sono elaborati prima del controllo.
`quota_censored` indica quota non raggiunta (esclusi annullamenti);
`logistics_open` indica attività logistiche non concluse. Il ritardo finale
rimane nullo per gli incompleti, senza sostituirlo con zero o con l'orizzonte.

### Prove eseguite

Suite del nuovo nucleo: **157 test passati**. Sono inclusi sei test del runner
su riproducibilità, scadenze da convenzione, estensione, attività di fondo,
input invalidi e completamento esattamente al limite.

Prove end-to-end con seed 0, un giorno di generazione più un giorno aggiuntivo:

| Profilo | Richieste | Quote ancora incomplete al limite | Arresto |
|---|---:|---:|---|
| Regolare | 3 | 1 | 172.800 s, limite temporale |
| Sotto pressione | 15 | 10 | 172.800 s, limite temporale |
| Perturbato | 3 | 2 | 172.800 s, limite temporale |

Conteggi casuali, non medie di profilo né metriche di validazione. Le code
emergono senza ridurre le richieste o forzare il bilanciamento degli esiti.

```bash
python -m src.logistics.experiments --profile regular --seed 0 --days 1 --extension-days 1
```

Il comando stampa JSON diagnostico, con configurazione, inizializzazione,
registro delle scadenze ed esiti. Non è ancora il dataset temporale senza
futuro previsto da D01. La CLI usa 1+1 giorni per la prova breve; `ScenarioConfig`
usa 7+7 giorni come default del progetto.
