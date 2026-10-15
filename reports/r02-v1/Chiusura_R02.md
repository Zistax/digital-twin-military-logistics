# R02 — consegna verificata offline, pubblicazione sospesa

**R02 è implementata e verificata nel perimetro offline richiesto dal proprietario.** La pubblicazione online non è stata eseguita: non è disponibile un hosting e la richiesta è di proseguire offline. Non si dichiara completata la consegna online delle 18 voci della roadmap.

## Risultato

La demo limitata ha una UI con quattro viste e un servizio dedicato. Visitatori senza token consultano gli aggregati del pilota R01 e i limiti M03. Le sessioni personali usano un preset sintetico e possono registrare missioni, avanzare, annullare e prendere decisioni di recupero. Le previsioni sperimentali richiedono una scelta esplicita; nessun modello viene promosso.

Token con scadenza fissa, proprietà della sessione, revoca, quote, limite di calcolo e persistenza SQLite sono implementati. I comandi sono ricostruiti nel proprio processo effimero; un timeout termina il processo senza commit. I retry restano idempotenti dopo il riavvio. Le attività complete di training/configurazione/registro rimangono negli strumenti locali, fuori dagli endpoint della demo.

## Verifica

- Suite completa su CPython 3.12.14 / Windows AMD64: **365 test + 16 sotto-test passati**, un test saltato perché Windows non concede la creazione di symlink. Copertura del nucleo **93,03%**, soglia 90%; Ruff e Black passati.
- 13 test R02 su accesso, isolamento fra visitatori, revoca, persistenza, retry, scadenza/pulizia, quote, preset, rate limit, timeout/kill, fingerprint e worker sperimentale reale.
- Prova dalla copia estratta in un percorso con spazi: **21 richieste HTTP reali passate**, con arresto e riavvio del server, ripresa dello stato, retry persistente, conflitto rifiutato, visitatori separati, amministratore protetto e revoca.
- Browser reale: creazione con candidato sperimentale, missione da 10 unità e quota 8, avanzamento a 300 s, ripristino dopo reload, quattro viste, aggregati e 49 criteri M03 falliti visibili. Sessione sintetica della prova poi revocata.
- Manifest dello ZIP verificato; runtime, database e chiavi esclusi. I checksum degli artefatti congelati disponibili restano invariati. Il payload voluminoso M02 separato non è stato scaricato né modificato.

La suite ha individuato un errore storico Windows nel batch D03: `write_text` convertiva i newline della traccia in CRLF, mentre il checksum era calcolato sui byte LF. La scrittura della sola nuova traccia ora usa esplicitamente byte UTF-8: l'audit completo dei 90 piccoli bundle di regressione passa. Nessun bundle D03 esistente, split, modello o test finale viene rigenerato o usato per tuning.

## Pacchetto e istruzioni

- [Guida di avvio, ruoli, limiti e distribuzione](../../docs/demo-r02.md)
- [Decisioni P17/P18](../../docs/decisioni-r02-v1.md)
- `digital-twin-demo-r02.zip` e `digital-twin-demo-r02.json`: pacchetto e checksum, distribuiti accanto a questo rapporto nella repository.
- [Verifica strutturata](verification.json)
- [Test R02](boundaries.xml), [prova HTTP estratta](http-extracted.json)
- [Qualità completa](../quality-r02-final-20261015/quality.json), [coverage](../quality-r02-final-20261015/coverage.json)
- [Anteprima](preview.jpg), [vista risultati](preview-results.jpg)

## Limiti e lavoro rimanente

Dockerfile e Compose sono predisposti ma **non costruiti/eseguiti**: il motore Docker Linux non è attivo sul computer di verifica. La verifica effettuata è quella nativa Windows, non quella container. L'immagine base mobile dovrà essere fissata per digest nella destinazione reale. Linux/macOS per R02 non sono stati provati in questa esecuzione; i rapporti R01 Linux restano evidenze separate.

La distribuzione resta a replica singola con SQLite locale. Il limitatore non è una difesa anti-DDoS; dietro un proxy i visitatori condividono prudentemente la quota del proxy, finché non venga verificata una configurazione di inoltro fidata. Nessuna garanzia di latenza/uptime pubblica viene dichiarata dai tempi locali. L'amministrazione completa è locale. L'installazione iniziale richiede dipendenze o wheel già disponibili; il servizio installato funziona offline.

Restano da completare prima di pubblicare: provider e costi, volume persistente, dominio/HTTPS, segreti e permessi della destinazione, build container, limiti e misure prestazionali sull'hosting, test finali di accesso/isolamento/retention nella destinazione e pubblicazione come azione separata. Nessun servizio a pagamento o account è stato attivato.
