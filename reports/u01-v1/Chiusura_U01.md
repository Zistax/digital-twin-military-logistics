# Chiusura U01 — API e quattro viste

**U01 completata nel perimetro locale: voce 16 di 18.** La dashboard Streamlit
usa `/v1` per missioni, depositi, flotta/rete e analisi. Gli endpoint del
prototipo storico restano compatibili e separati dal flusso nativo.

## Funzionalità verificate

- Sessioni isolate con identità di simulazione distinta, cutoff, revisione,
  mutazioni atomiche, retry/conflitti e chiusura; limiti locali documentati.
- Missioni manuali con quote per articolo; annullamento con motivo; richieste
  generate ammesse solo al proprio istante, senza rendere pubblico il futuro.
- Recuperi osservati e decisioni manuali approve/defer/reject; approvazioni
  automatiche disattivate nella demo interattiva.
- Stock, riserve, capacità/occupazione, forniture promesse, backlog dovuto,
  banchine/code e quarantena; flotta, carichi, tratte e condizioni osservate.
- Fatti, stima iniziale del pianificatore e previsione ML distinti; timestamp,
  storico, astensione e arresto a quota/annullamento. Il servizio congelato M02
  conserva scadenza esatta e cadenza di 1800 s. Il chiamante U01 confronta risorse
  pubbliche dopo ogni batch di tick (300 s) per aggiornare anche a variazioni
  di percorso/disponibilità a fase e quantità di missione immutate.
- Quote raggiunte, missioni aperte e annullate contate separatamente;
  puntualità con denominatore, utilizzo corrente flotta e storici di attesa,
  fasi e viaggi a vuoto. Valutazione storica M03 separata dalla sessione viva:
  baseline, errori, calibrazione, copertura/ampiezza, segmenti e gate.

## Modelli e informazioni nascoste

Il registro conserva **active=null**. La modalità approvata rifiuta l'avvio
con 409 senza fallback; il default non carica ML. Solo una scelta esplicita
abilita m02-v1 sperimentale, con verifica checksum e dicitura NON PROMOSSO.
Modelli ed evidenze congelate M03 sono invariati byte per byte. Nessun nuovo
training o tuning sul test già consumato; nessuna promozione.

Le risposte sono proiezioni esplicite, non snapshot integrali del simulatore.
I test dimostrano che danni non ispezionati e valori effettivi futuri di una
fornitura non cambiano la vista o la firma delle risorse pubbliche. I danni
ispezionati diventano visibili all'istante corretto. Sono esclusi esposizione
latente, orari futuri di approvazione/riparazione, selezioni interne e richieste
non ancora create. Una violazione degli invarianti invalida la sessione;
input errati vengono rifiutati senza mutazioni parziali.

Restano i limiti M03: **49 gate falliti**, durate condizionate/censurate con
errori elevati, intervalli molto ampi e copertura non validata statisticamente
per ogni aggiornamento a 30 minuti/eventi. Collegare il servizio alla UI non
rende il candidato idoneo all'uso operativo.

## Validazione

Suite finale completa: **348 test e 16 sotto-test passati**.
Copertura del nucleo: **93.01%**, soglia ≥90%. Ruff e Black passati.
I 19 test mirati API/Streamlit coprono flussi, isolamento, retry, invalidazione,
separazione del futuro e aggiornamenti delle previsioni. AppTest Streamlit
1.66.0 usa il vero backend FastAPI in processo e verifica quattro schede,
creazione missione, avanzamento, refresh e chiusura. Resta l'avviso esterno
di deprecazione Starlette/httpx già noto.

- [Rapporto qualità finale](../quality-u01-final-20261015/quality.json)
- [Copertura dettagliata](../quality-u01-final-20261015/coverage.json)
- [Verifica e checksum](verification.json)
- [Schema OpenAPI](openapi.json)
- [Avvio e API/UI](../../docs/api-ui-u01.md)

La prima suite da 347 test è conservata in `quality-u01-20261015`;
la suite finale aggiunge la regressione sugli aggiornamenti delle risorse.
Il checkpoint precedente alla suite completa è tracciato in `checkpoint.json`.

## Perimetro e lavoro restante

Uso locale su loopback, un worker, sessioni in memoria perse al riavvio;
limiti descritti nella guida. Posizioni nodali/tratte, non GPS. Missioni
aperte a fine orizzonte censurate; annullate escluse dal conteggio delle aperte.
La UI inserisce un articolo alla volta; l'API supporta fino a 15 articoli.
L'import con quarantena resta disponibile nei contratti D01, non è un nuovo
modulo di caricamento nella UI U01.

Prossime voci: **R01 (17/18), pacchetto locale completo**, poi **R02 (18/18),
demo online limitata** con autenticazione/ruoli, persistenza multiutente,
limiti online e hosting. Nessun deploy pubblico viene dichiarato in U01.
