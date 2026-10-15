# R02 — otto visitatori e pulizia periodica, verifica locale

La prova usa Docker Linux amd64, 1 CPU, 768 MiB, 8 sessioni e un solo processo di simulazione. Non è un test su hosting pubblico. I risultati sono quelli di questo computer e di un campione limitato.

## Problemi trovati e correzioni

Il limite del server era di 8 connessioni HTTP. La versione installata di Uvicorn rifiuta le richieste quando il numero di connessioni è maggiore o uguale al limite, comprendendo le connessioni ancora aperte. Nella prova iniziale, 9 letture pubbliche su 24 hanno ricevuto 503. Il launcher ora riserva **16 connessioni HTTP** per servire gli 8 visitatori; capacità delle sessioni, quote, memoria e singolo worker di simulazione restano invariati.

La quota di 5 emissioni di accesso al minuto veniva applicata per percorso, anche a `DELETE /demo/access`. La chiusura poteva quindi essere rifiutata con 429 quando le emissioni erano esaurite. La quota speciale ora riguarda solo `POST /demo/access`; la revoca continua a rispettare i limiti generali. Il test di regressione verifica che una chiusura funzioni senza permettere altre emissioni oltre quota.

## Risultati osservati

| Prova | Risultato locale |
|---|---|
| Sessioni | 8 identità distinte; nona sessione rifiutata |
| Letture simultanee | 2 raffiche da 8 richieste, **16/16 risposte 200** |
| Tempo delle letture | p95 empirico **0,1493 s**, obiettivo locale <1 s; solo 16 campioni |
| Isolamento | Nessun risultato incrociato; 8 tentativi su sessioni altrui rifiutati con 404 |
| Mutazioni simultanee | 2 completate, 6 risposte 503 di servizio occupato; stato coerente con gli esiti |
| Processi di simulazione | Massimo osservato **1**, con campionamento durante la raffica |
| Scadenza periodica | Lease di prova impostato a `now+2 s`; rimozione osservata circa **29,6 s** dopo la scadenza |
| Cascata | Prima: 1 lease, 1 sessione, 1 comando; dopo: tutti a zero |

Il p95 usa nearest rank. Non dimostra una latenza di produzione o descrive le letture durante una mutazione. I 503 sotto saturazione sono deliberati: non si avviano otto processi per soddisfare la raffica. I visitatori possono aggiornare e riprovare; nessuna mutazione rifiutata risulta salvata.

La prova rispetta le quote: dopo i primi 5 token aspetta il minuto successivo, senza azzerare contatori o modificare il tempo del server. Viene anticipata solo la scadenza di un lease sintetico, senza attendere 30 minuti reali. Per osservare la pulizia il checker legge direttamente SQLite: non invoca API di lettura/manutenzione che cancellerebbero i record. Gli healthcheck restano attivi ma non accedono al database.

## Ripetizione su progetto vuoto

Richiede Docker Desktop con motore Linux, client Docker e Python sul computer di controllo. Usare un progetto dedicato e vuoto: il controllo crea e revoca/scade i propri accessi sintetici.

```powershell
$env:DEMO_PORT='18081'
docker compose -p logistics-r02-check-load -f deploy/compose.yaml up --build -d --wait
python scripts/check_demo_load.py --report reports/prova-carico.json
```

Il controllo attende il normale rinnovo della quota e il ciclo di pulizia. Non usarlo sulla demo personale e non inviare altre richieste durante la prova. Nessun token o chiave è scritto nel rapporto.

La regressione container può essere ripetuta sullo stesso progetto, quando è vuoto e c'è una finestra di quota libera:

```sh
python scripts/check_container_demo.py --project logistics-r02-check-load --port 18081 --report reports/prova-container-carico.json
```

Per ricostruire la consegna con le evidenze finali:

```sh
python scripts/build_demo_package.py --include-load-report --output reports/r02-load-v1/digital-twin-demo-r02-load.zip
```

Il costruttore verifica i checksum di runtime, launcher e prove container/carico. Le consegne precedenti sono conservate e non vengono sovrascritte.

## Limiti mantenuti

Hosting, HTTPS, storage, segreti e misure nella destinazione reale restano sospesi. Questo campione locale non li sostituisce, non prova una disponibilità pubblica né la resistenza ad attacchi distribuiti. La durata nominale di 30 minuti è testata logicamente e con scadenza controllata, non attendendo 30 minuti reali.
