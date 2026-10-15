# R02 — container locale verificato

Il container è stato costruito e provato su Docker Desktop/WSL2, Linux amd64, il 15 ottobre 2026. Nessun hosting pubblico, account cloud o servizio a pagamento è stato attivato. La verifica integra quella nativa Windows di R02, senza sostituirla.

La nuova consegna è `reports/r02-container-v1/digital-twin-demo-r02-container.zip`; il precedente ZIP `reports/r02-v1/digital-twin-demo-r02.zip` rimane invariato come fotografia della consegna offline iniziale. Per la ricetta container verificata usare la nuova consegna o il checkout Git aggiornato.

Per ricostruire la nuova consegna con il rapporto container incluso:

```sh
python scripts/build_demo_package.py --include-container-report --output reports/r02-container-v1/digital-twin-demo-r02-container.zip
```

Il costruttore controlla che i sorgenti runtime e la configurazione corrispondano ai checksum verificati nell'immagine: rifiuta l'etichetta “container verificato” se i file sono cambiati dopo la prova. Dopo una modifica del runtime occorre ricostruire l'immagine e ripetere la verifica.

## Avvio sul computer

Docker Desktop deve essere avviato con il motore Linux. Dalla cartella della nuova consegna:

```powershell
$env:DEMO_PORT='18080'
docker compose -p logistics-demo -f deploy/compose.yaml up --build -d --wait
```

Su Linux/macOS la stessa variabile si imposta prima del comando:

```sh
export DEMO_PORT=18080
docker compose -p logistics-demo -f deploy/compose.yaml up --build -d --wait
```

Aprire <http://127.0.0.1:18080>. La prima build scarica immagine e dipendenze; gli avvii successivi usano l'immagine locale. Se `DEMO_PORT` non è impostata, la porta predefinita è 8080. Il binding è sempre su `127.0.0.1`, anche usando una porta diversa. La demo nativa già presente su 8080 può restare aperta.

La base ufficiale Python è fissata nel Dockerfile al digest multiarch `sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`. La piattaforma effettivamente provata è solo `linux/amd64`, con CPython 3.12.15 e dipendenze bloccate; ARM64 e altri motori non sono dichiarati verificati. Il digest fissa la base, non garantisce immagini finali identiche byte per byte fra build: i metadati di build e le attestazioni possono cambiare.

## Stato, arresto e persistenza

```sh
docker compose -p logistics-demo -f deploy/compose.yaml ps
docker compose -p logistics-demo -f deploy/compose.yaml stop
docker compose -p logistics-demo -f deploy/compose.yaml up -d --wait
```

Database SQLite e chiave amministrativa sono nel volume `demo-runtime` del progetto Compose. Arresto, riavvio e ricreazione del container conservano le sessioni non scadute, purché non si elimini il volume e si usi la stessa release. La chiave non è nell'immagine e viene creata nel volume con proprietario UID 10001 e permessi 0600.

Per lo stato amministrativo dall'interno del container, il comando usa la porta **interna** 8080; la porta del browser può essere diversa:

```sh
docker compose -p logistics-demo -f deploy/compose.yaml exec -e DEMO_PUBLIC_ORIGIN=http://127.0.0.1:8080 demo python scripts/run_demo.py --status
```

Non servono chiavi nella riga di comando: il programma legge la chiave del volume. Il cambio di origine qui riguarda solo la chiamata amministrativa interna; non cambia l'origine configurata del servizio già avviato.

Il comando `down` rimuove container e rete, conservando il volume; `down --volumes` elimina anche database e chiave. Quest'ultima operazione è adatta soltanto a dati di prova da scartare. Prima di aggiornare codice/artefatti, rispettare la procedura di scadenza/drain descritta nella [guida R02](demo-r02.md): i journal vivi di release diverse non vengono migrati automaticamente.

## Prova ripetibile, su progetto dedicato

Il controllo ricrea il container e forza la scadenza dei soli due accessi sintetici creati dal controllo. Usare un progetto **vuoto**, distinto dalla demo personale:

```powershell
$env:DEMO_PORT='18080'
docker compose -p logistics-r02-check -f deploy/compose.yaml up --build -d --wait
python scripts/check_container_demo.py --project logistics-r02-check --port 18080 --report reports/prova-container.json
```

Il checker richiede soltanto Python con libreria standard e il client Docker sul computer di controllo. Rifiuta un progetto non chiamato `logistics-r02-check...` o con accessi/sessioni già presenti. Non stampa né salva i token o la chiave amministrativa nel rapporto. Le sessioni di prova vengono revocate/scadute al termine della prova riuscita.

La prova verificata copre:

- 24 richieste HTTP reali: preset, missione, avanzamento, limiti, revisione obsoleta, ruoli, origine non consentita e proprietà della sessione.
- Ricreazione effettiva del container mantenendo soltanto il volume, ripresa dello stato e retry persistente; tentativo di cambiare i dati di un retry rifiutato.
- Processo di simulazione reale terminato per timeout controllato a 1 ms, nessun worker rimasto e stato precedente intatto. È una prova della stessa procedura di kill, non un'attesa di 20 secondi.
- Scadenza controllata del lease sintetico nel database, rifiuto dell'accesso e pulizia su richiesta. Non sono stati attesi 30 minuti reali e non è stato cambiato l'orologio del computer.
- Utente UID 10001, filesystem di sistema in sola lettura, chiave 0600, `pip check`, healthcheck, 768 MiB RAM, 1 CPU, 64 processi, capability rimosse e `no-new-privileges`.

I tempi nel rapporto sono misure locali di richieste sequenziali, non un benchmark pubblico o una prova di carico a otto visitatori. La suite completa precedente resta **365 test + 16 sotto-test su Windows**; non è stata rieseguita interamente nell'immagine di produzione, che non include dipendenze di test.

## Lavoro ancora aperto

Restano provider/costi, dominio e HTTPS, storage e segreti del provider, prova del carico/isolamento/retention nella destinazione e pubblicazione separata. Questa verifica non espone il servizio su Internet. Il volume Docker del computer non equivale a un backup o a uno storage ospitato.
