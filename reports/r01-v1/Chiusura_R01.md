# Chiusura R01 — pacchetto locale riproducibile

**R01 completata nel perimetro verificato: voce 17 su 18.**

Disponibile [digital-twin-local-r01.zip](digital-twin-local-r01.zip):
1950090 byte, 250 file di sorgenti/configurazioni/documentazione,
CLI, modelli candidati e rapporti necessari. Manifest SHA256 incluso. Due build
dallo stesso contenuto e base hanno prodotto gli stessi byte.

## Consegna

- `requirements-local.in` e lock completo `requirements-local.txt`, coerente
  con lo stack scientifico congelato; installazione in venv con controllo pip.
- `setup_local.py` e `local_demo.py doctor/smoke/serve/check-servers`;
  avvio su loopback di API e Streamlit, porte configurabili, readiness e cleanup.
- Diagnostica di versioni, integrità del pacchetto e registro; nessuna promozione.
- Sperimentazione nativa e CLI di previsione; istruzioni per ripristino dei dati
  D03 e refit separati, senza incorporare GB nel pacchetto della demo.

## Problema trovato dalla prova pulita

Il caricamento U01 dipendeva involontariamente dal `PYTHONPATH` dei test:
i pickle congelati fanno riferimento al nome storico `logistics`. La nuova
compatibilità in `src/api/model_compat.py` risolve i nomi verso gli stessi moduli
fisici e rifiuta collisioni con moduli estranei. Non modifica i pickle o il codice
ML congelato. Il launcher passa inoltre l'URL API selezionato alla dashboard.

## Evidenza end-to-end

Prova su **CPython 3.12.14, Linux x86_64**:

1. Primo ambiente vuoto: dipendenze bloccate installate, `pip check` passato,
   smoke nativo e processi reali API/Streamlit verificati.
2. ZIP estratto in un percorso con spazi; secondo ambiente vuoto installato con
   lo script distribuito. Nessun pacchetto globale necessario.
3. Manifest verificato, missione/quote/retry, cadenza/scadenza della previsione,
   annullamento/arresto, rifiuto della modalità approvata e recupero manuale passati.
4. API e Streamlit reali avviati dalla copia estratta. AppTest usa l'API HTTP,
   abilita esplicitamente il candidato, crea sessione e missione, avanza, aggiorna
   e chiude. I due server vengono poi arrestati.
5. Previsione CLI da snapshot pubblicato e pilota nativo seed 3, tre profili,
   1 giorno + 1 di estensione: tre run validi con export/rilettura dei bundle.
   Il pilota è esplorativo, non nuova validazione ML.
6. `doctor` finale conferma intatti i file del manifest dopo tutte le prove.

Suite completa: **353 test + 16 sotto-test**, copertura nucleo
**93.03%**; Ruff e Black passati. Controlli dedicati dei nuovi script
e cinque test di rilascio ripetuti dopo gli ultimi affinamenti di metadati/base.
Resta l'avviso esterno di deprecazione Starlette/httpx.

## Risultati e riproduzione

- [Guida di installazione e uso](../../docs/pacchetto-locale-r01.md)
- [Verifica strutturata](verification.json), [manifest e checksum ZIP](digital-twin-local-r01.json)
- [Smoke dalla copia estratta](smoke-extracted.json), [processi reali e UI](servers-extracted.json)
- [Integrità finale](doctor-extracted-final.json), [ricostruzione identica](rebuild-check.json)
- [Pilota](pilot-summary.json), [bundle e trace nativi del pilota](pilot-native.zip)
- [Qualità completa](../quality-r01-20261015/quality.json) e [coverage](../quality-r01-20261015/coverage.json)

## Limiti mantenuti

I comandi Windows/macOS sono predisposti ma non eseguiti su quei sistemi;
Python 3.13 non è il runtime validato. Il pacchetto non incorpora Python né
le wheel: la prima installazione richiede rete oppure un wheelhouse per la
stessa piattaforma, preparabile con le istruzioni. I dati voluminosi restano
separati e i payload esclusi sono elencati nel manifest. Le sessioni della UI
sono in memoria, un worker, senza persistenza multiutente.

Modelli ed evidenze congelate M03 invariati byte per byte; **active=null**,
49 gate M03 falliti e limiti statistici ancora visibili. Nessun training o tuning
sul test consumato, nessuna promozione e nessun deploy online.

Resta **R02 (18/18): demo online limitata**, con accessi/ruoli, isolamento,
persistenza, limiti operativi, hosting e pubblicazione da verificare separatamente.
