# R02 — verifica del container locale

**Build e verifica del container completate nel perimetro locale Linux amd64.** Il precedente limite “motore Docker non attivo” è superato: Docker Desktop è stato avviato e l'immagine è stata costruita e provata. La pubblicazione online resta sospesa, come richiesto dal proprietario.

## Risultato verificato

- Immagine ufficiale Python fissata per digest, CPython 3.12.15; installazione del lock runtime e `pip check` passati.
- 24 controlli HTTP reali passati su `127.0.0.1:18080`, con candidato sperimentale esplicito, missione da 10 unità/quota 8, avanzamento a 300 s, proprietà della sessione, limiti e ruoli.
- Container ricreato, con ID differente e stesso volume: stato e retry originari conservati, retry conflittuale rifiutato.
- Timeout controllato del processo reale: 503, nessun worker rimasto e nessuna mutazione dello stato precedente. Budget ridotto a 1 ms solo per l'iniezione di errore nel processo amministrativo di prova.
- Revoca di un visitatore e scadenza forzata del solo altro lease di prova, con eliminazione finale di lease, sessioni e comandi. Nessun orologio di sistema modificato.
- UID 10001, chiave amministrativa nel volume con permessi 0600, root filesystem in sola lettura, memoria 768 MiB, 1 CPU, 64 processi, capability rimosse, `no-new-privileges`, healthcheck positivo e binding solo loopback verificati sul container reale.

106 checksum verificano la corrispondenza fra runtime nell'immagine e sorgenti/configurazione da consegnare. Quattro test del costruttore del pacchetto rifiutano evidenze mancanti, obsolete e con percorsi non sicuri; il costruttore non assegna l'etichetta “container verificato” a sorgenti modificati dopo la prova.

La ricetta ora include soltanto il protocollo necessario ai riferimenti M03 e la licenza, anziché tutta la documentazione nell'immagine. La porta esterna può essere selezionata con `DEMO_PORT`, mantenendo il binding su `127.0.0.1`. Nessun codice del simulatore, pipeline ML o artefatto congelato viene modificato in questa consegna.

## Evidenze e riproduzione

- [Guida del container e della prova](../../docs/container-r02.md)
- [Verifica strutturata, immagine, ambiente e tempi](verification.json)
- [Test del costruttore](package-tests.xml)
- `digital-twin-demo-r02-container.zip` e relativo `.json`: nuova consegna sorgenti con manifest; il precedente ZIP R02 resta invariato.
- La suite **365 test + 16 sotto-test**, un symlink saltato e copertura nucleo **93,03%** è quella Windows della consegna [R02 offline](../r02-v1/Chiusura_R02.md), distinta dai 24 controlli container di questo rapporto.

## Limiti mantenuti

Non è una prova su hosting pubblico, ARM64 o più repliche. Le richieste sono sequenziali: i tempi locali non dimostrano latenza p95 o capacità con otto visitatori concorrenti. La scadenza è stata provocata sul lease di prova; non sono stati attesi 30 minuti reali. Il percorso di timeout è stato provato con budget di 1 ms, senza alterare il default del servizio a 20 secondi.

Restano da scegliere e verificare provider/costi, dominio/HTTPS, volume persistente e segreti ospitati, carico/isolamento/retention nella destinazione e pubblicazione. Nessun modello attivo, nessun nuovo training, nessun servizio a pagamento e nessun deploy pubblico.
