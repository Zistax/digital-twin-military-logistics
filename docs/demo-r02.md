# R02 — demo limitata, verificabile offline

Il servizio dimostrativo R02 usa lo stesso nucleo di R01, con un ingresso separato e limiti più stretti. La pubblicazione su Internet non è stata eseguita: il proprietario non dispone di un hosting e ha chiesto di proseguire offline. Nessun account cloud, dominio o servizio a pagamento attivato.

## Avvio sul computer

Richiede Python 3.12 e le dipendenze `requirements-local.txt`. Dalla cartella estratta, usare un'installazione Python 3.12 completa (con `venv` e `ensurepip`):

```powershell
py -3.12 scripts/setup_local.py
.venv/Scripts/python.exe scripts/run_demo.py
```

Su Linux/macOS:

```sh
python3.12 scripts/setup_local.py
.venv/bin/python scripts/run_demo.py
```

Aprire <http://127.0.0.1:8080>. Il primo avvio genera una chiave amministrativa in `runtime/demo-admin.key`, mai stampata. Database e chiave restano fuori da Git e dagli ZIP. `Ctrl+C` arresta il servizio; il riavvio conserva le sessioni non scadute. Le schede del browser conservano il token temporaneo in `sessionStorage`: perdere tale token impedisce di riprendere la sessione. Non vengono creati account personali.

Una Python incorporata priva di `ensurepip` non può usare direttamente lo script di installazione: usare una distribuzione completa o installare il lock nel proprio ambiente Python 3.12 con un pip compatibile. La prima installazione richiede rete o un wheelhouse della stessa piattaforma. Dopo l'installazione, il servizio, il simulatore e la UI funzionano offline, senza CDN o chiamate cloud.

Per ricostruire il pacchetto:

```sh
python scripts/build_demo_package.py --output reports/r02-v1/digital-twin-demo-r02.zip
```

Lo ZIP include codice, modelli candidati, documenti, asset della UI e `DEMO-MANIFEST.json` con checksum. Non include ambienti virtuali, chiavi, database, sessioni di prova o dataset D03 voluminosi. Il pacchetto originale R01 rimane invariato.

Per ripetere la prova con processi reali, riavvio e due visitatori isolati:

```sh
python scripts/check_demo.py --report reports/prova-r02-http.json
```

La prova crea un database temporaneo e una chiave temporanea, esegue i controlli su loopback e poi arresta i server e rimuove il runtime di prova. Non riutilizza il database della demo aperta dall'utente.

## Ruoli e perimetro

| Accesso | Funzioni consentite |
|---|---|
| Visitatore senza token | Tre risultati aggregati del pilota R01, catalogo, limiti e rapporto M03 |
| Sessione temporanea | Preset regular/seed 0; missioni, avanzamento, cancellazioni e decisioni manuali nel proprio scenario |
| Amministratore | Stato del servizio e pulizia dei record scaduti tramite bearer separato |
| Amministrazione completa locale | Configurazioni, dataset, training, registro, approvazione/rollback attraverso gli strumenti locali già esistenti |

Le operazioni amministrative pesanti non sono endpoint remoti. Non sono esposti gli endpoint del prototipo `/simulate` e `/predict`, il training, la modifica del catalogo o la promozione dei modelli. La UI completa Streamlit e l'API locale U01/R01 restano disponibili separatamente. R02 aggiunge una piccola UI web nello stesso servizio FastAPI per evitare di distribuire un'API non protetta dietro la UI.

Per lo stato amministrativo, dalla stessa installazione che conserva la chiave:

```sh
python scripts/run_demo.py --status
python scripts/run_demo.py --cleanup
```

`DEMO_ADMIN_SECRET` può sostituire la chiave su file: minimo 32 caratteri, generati casualmente e forniti tramite secret manager, mai nel sorgente. La chiave serve anche a derivare gli identificatori dei token; cambiarla invalida gli accessi esistenti. Non esiste login amministrativo nel browser.

## Limiti verificabili

| Risorsa | Limite |
|---|---|
| Validità accesso | 1800 secondi fissi, senza rinnovo automatico |
| Sessioni simultanee | 8 globali; 1 per token |
| Accessi temporanei | 64 globali fino a scadenza/revoca |
| Comandi | 24 per sessione; retry identici non consumano altri comandi |
| Missioni manuali | 5 per sessione; max 3 articoli e 100 unità totali per inserimento |
| Scenario | regular, seed 0; max 3600 secondi simulati, passi di max 300 secondi |
| Corpo HTTP | 8192 byte; lettura entro 5 secondi |
| Calcolo | Un processo di simulazione alla volta; budget wall-clock 20 secondi, poi arresto e nessun commit |
| Risposta persistita | Max 512 KiB per nuovo comando |
| SQLite | Max 16384 pagine, circa 64 MiB con pagine di default |
| Richieste | 60/minuto per indirizzo visto dal servizio, 180/minuto globali |
| Emissione token | 5/minuto per indirizzo visto dal servizio |
| Server | Un worker, concorrenza HTTP 16 per 8 visitatori, backlog 16, keepalive 5 secondi |

Gli errori 429 indicano quote esaurite; 503 indica servizio occupato, storage indisponibile o budget di calcolo superato. La finestra di rate limiting è al minuto: non è un sistema anti-DDoS. Le intestazioni proxy non sono considerate attendibili: dietro un reverse proxy i visitatori condividono prudentemente la quota del proxy. Non attivare l'attendibilità di `X-Forwarded-For` da Internet senza una configurazione verificata.

## Persistenza, isolamento e retention

SQLite conserva hash HMAC dei token, configurazione iniziale, comandi ordinati e sole viste osservabili già proiettate dall'API nativa. Non salva pickle dello stato di sessione. Ogni mutazione ricostruisce il proprio scenario in un processo separato e applica il journal; la risposta è salvata insieme al comando in una transazione atomica. Nessun dato di sessione viene caricato da un altro visitatore. Un ID valido appartenente a un altro token risponde 404, anche per modifica e cancellazione.

I retry con stesso identificatore e stessi dati restituiscono la risposta originaria, anche dopo un riavvio; dati diversi con lo stesso identificatore rispondono 409. Revisioni obsolete rispondono 409. Timeout ed errori del worker lasciano invariati vista e journal precedenti. Anche dopo il calcolo viene ricontrollata la scadenza dell'accesso.

Gli accessi scadono dopo 30 minuti anche a servizio spento. Alla ripartenza vengono eliminati; mentre il servizio è attivo la pulizia avviene ogni 30 secondi e sulle richieste soggette a quote. Il periodo può allungarsi fino al termine di una transazione di simulazione in corso (max 20 secondi, salvo overhead del sistema). La revoca con `DELETE /demo/access` elimina subito accesso, sessione e comandi. Il pulsante di chiusura della UI esegue la revoca. Gli IP non vengono memorizzati in chiaro; le chiavi delle quote sono HMAC e sono ripulite dopo la finestra utile. Gli access log HTTP sono disattivati nel launcher. Nessuna raccolta di nomi, email o dati reali; inserire soltanto dati sintetici.

Il database usa `secure_delete`; questa è eliminazione logica dei record nel database gestito, non una garanzia di cancellazione forense da dischi, snapshot o backup del provider. Non sono configurati backup automatici delle sessioni temporanee. Proteggere la cartella runtime con permessi dell'utente del servizio.

Il fingerprint della release include codice simulatore/API e worker, artefatti `.joblib`, registro e lock runtime. Una release diversa rifiuta il riuso di sessioni vive: attendere la scadenza o revocare, arrestare, archiviare/eliminare il runtime con procedura amministrativa e poi aggiornare. Nessuna migrazione implicita dei journal. Deploy a replica singola con storage locale persistente; più repliche o database di rete non sono supportati.

## Container locale verificato, hosting non eseguito

`deploy/Dockerfile` e `deploy/compose.yaml` sono stati costruiti e provati su Docker Desktop/WSL2, Linux amd64, CPython 3.12.15. Utente non privilegiato, filesystem di sistema in sola lettura, volume runtime, limite 768 MiB/1 CPU/64 processi e healthcheck sono stati verificati sul container reale. Il binding predefinito è solo `127.0.0.1:8080`; `DEMO_PORT` permette di cambiare la porta locale. Vedere la [guida aggiornata del container](container-r02.md) e il [rapporto integrativo](../reports/r02-container-v1/Chiusura_Container.md). Il precedente ZIP R02 resta una fotografia della verifica Windows iniziale.

```sh
docker compose -f deploy/compose.yaml up --build -d
```

L'immagine base `python:3.12-slim` è ora fissata nel Dockerfile al digest verificato, indicato nel rapporto integrativo. Prima di un hosting reale servono: scelta e costo del provider, storage persistente, reverse proxy HTTPS con dominio corretto in `DEMO_PUBLIC_ORIGIN`, permessi/segreti, limiti del provider e misure prestazionali nella destinazione. L'app rifiuta un'origine HTTP pubblica; il solo HTTP consentito è loopback/test. Non esporre l'API locale completa U01 e non inoltrare la porta senza TLS.

Obiettivi per la prova sul futuro hosting: letture di sessione p95 sotto 1 secondo in assenza di una mutazione in corso, creazione e mutazione sotto 20 secondi, 8 accessi concorrenti senza fuga di dati, test di riavvio e scadenza. Questi sono criteri di accettazione, non prestazioni pubbliche già misurate. Rimangono da verificare la capacità e l'overhead del provider e la protezione di rete; nessuna promessa di disponibilità o resistenza ad attacchi distribuiti.

La pubblicazione è un'azione separata, rimasta sospesa per richiesta del proprietario. Nessuna URL online o certificazione di produzione viene dichiarata.
