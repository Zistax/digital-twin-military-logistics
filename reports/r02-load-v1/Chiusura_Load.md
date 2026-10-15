# R02 — accessi concorrenti e pulizia periodica verificati offline

**Prova locale con otto visitatori completata.** Trovati e corretti due problemi del punto di accesso: rifiuti prematuri per concorrenza HTTP e quota di emissione token applicata anche alla revoca. Nessuna modifica a simulatore, modelli, dati di valutazione o criteri di promozione.

## Correzioni dimostrate

- Prima: 9 risposte 503 su 24 letture simultanee del catalogo con limite HTTP 8. Dopo: 16/16 letture delle sessioni riuscite, in due raffiche da otto visitatori, con limite HTTP 16. Le sessioni restano 8 e il processo di simulazione resta uno.
- Prima: la regressione sulla revoca con quota di emissione esaurita ottiene 429. Dopo: la revoca funziona, ma una nuova emissione resta limitata. Il contatore speciale si applica solo al POST di `/demo/access`.

## Risultati locali

- 8 sessioni distinte e nona sessione rifiutata; 8 tentativi su sessioni altrui rifiutati; nessun dato incrociato nelle risposte riuscite.
- 16 letture simultanee con p95 empirico **0,1493 s** (16 campioni, obiettivo locale <1 s).
- Raffica di 8 avanzamenti: **2 successi e 6 risposte 503** di saturazione. Revisioni coerenti con ciascun esito e nessun commit per le mutazioni rifiutate. Massimo osservato: **un processo di simulazione**.
- Pulizia periodica osservata senza API che accedano al database: dopo scadenza sintetica a `now+2 s`, rimozione dopo circa **29,6 s**. Prima: lease/sessione/comando presenti; dopo: tutti a zero. Gli healthcheck non attivano questa pulizia.
- Quote rispettate, con normale attesa del rinnovo del minuto. Nessun contatore azzerato durante la misura, nessuna modifica dell'orologio e nessun token esportato.
- Ripetuti anche i **24 controlli container** sulla stessa immagine corretta, compresa ricreazione con volume, retry, timeout controllato, revoca e vincoli di esecuzione. Verificata la corrispondenza dei 106 file runtime/configurazione.

## Qualità e consegna

Suite completa Windows: **378 test e 16 sotto-test passati**, un test symlink saltato per privilegio non disponibile. Copertura nucleo **93,03%**, soglia 90%; Ruff e Black passati. I 12 test del costruttore del pacchetto sono inclusi nella suite e rifiutano evidenze obsolete/non sicure per entrambe le versioni di consegna.

- [Guida e limiti](../../docs/carico-r02.md)
- [Prova concorrente e tempi](verification.json)
- [Regressione container sulla stessa immagine](container-verification.json)
- [Ammissione prima della correzione](admission-before.json)
- [Revoca prima della correzione](revocation-before.xml)
- [Test del pacchetto](package-tests.xml)
- [Suite completa](../quality-r02-load-final-20261015/quality.json), [coverage](../quality-r02-load-final-20261015/coverage.json)
- `digital-twin-demo-r02-load.zip`: nuova consegna con manifest e checksum; ZIP precedenti conservati.

## Limiti

Campione piccolo, computer locale, Linux amd64 e un indirizzo client: nessuna promessa di latenza/capacità su hosting futuro. Il calcolo resta limitato, con retry quando il servizio è occupato. La scadenza di un lease è stata anticipata per verificare il ciclo periodico: non sono stati attesi 30 minuti reali. Modelli ed evidenze congelate restano invariati, senza nuovo training o promozione.

Restano provider/costi, dominio/HTTPS, storage e segreti ospitati, carico e retention sul provider e pubblicazione separata. Nessun account cloud, servizio esterno o hosting pubblico attivato.
