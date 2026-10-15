# U01 — API native e quattro viste locali

La dashboard usa il nuovo nucleo operativo tramite `/v1`. Gli endpoint storici
`/predict`, `/predict_risk` e `/simulate` rimangono compatibili con il prototipo;
non alimentano le viste native.

## Avvio

Dalla radice della repository, in un ambiente Python con dipendenze installate:

```bash
python -m pip install -r requirements.txt -r requirements-quality.txt
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --workers 1
```

In un secondo terminale:

```bash
python -m streamlit run src/ui/dashboard.py --server.address 127.0.0.1
```

Aprire `http://127.0.0.1:8501`; documentazione API a `http://127.0.0.1:8000/docs`.
Creare una sessione dalla barra laterale. Si può inserire subito una missione
manuale oppure avanzare lo scenario di un'ora. Per il seed 0 la prima richiesta
generata arriva a t=43850 s: prima di allora una lista vuota è corretta.

## Viste

| Vista | Funzioni |
|---|---|
| Missioni e previsioni | Quote per articolo, riserve e accettato dopo ispezione, stato/scadenza/esiti, stima iniziale di pianificazione distinta da ML, ultima previsione con timestamp e astensione, storico; creazione e annullamento missioni; decisioni sui recuperi |
| Depositi e scorte | Stock disponibile e riservato, capacità/occupazione, forniture promesse/in attesa, backlog locale già dovuto, banchine, code e quarantena |
| Flotta e rete | Posizione nodale o tratta, assegnazioni/carichi/capacità/freddo, guasti osservati, percorsi e condizioni osservate |
| Analisi e qualità modello | Quote raggiunte, aperte e annullate separate, puntualità con denominatore esplicito, utilizzo corrente flotta e storici di attesa/fasi/viaggi; baseline, errori, calibrazione, intervalli e gate M03 |

I dettagli JSON sono espandibili. Posizioni e tratte non sono presentate come GPS
misurato. I fattori del predittore non sono spiegazioni causali.

## Registro e previsioni

Il default è `forecast_mode="off"`: le operazioni funzionano senza caricare ML e
la previsione dichiara astensione. `approved` richiede un modello attivo eleggibile:
attualmente restituisce 409, perché **active=null**. Non esiste fallback implicito.

La casella esplicita della UI sceglie `experimental`: carica m02-v1 verificando
checksum di artefatto, valutazione e riferimenti e mostra **NON PROMOSSO**.
Registro, modelli ed evidenze M03 non vengono riscritti; nessun nuovo training.
Gli aggiornamenti riusano il servizio M02 a creazione, cadenza di 1800 s, scadenza
esatta e cambiamenti osservabili. Percorsi, disponibilità, scorte, incidenti e
forniture pubblici sono confrontati dopo ogni batch di tick (300 s); variazioni
attivano un aggiornamento anche a fase e quantità di missione invariate.
La previsione si arresta a quota o annullamento.

I 49 gate M03 falliti restano visibili: errori elevati, intervalli molto ampi e
copertura statistica non validata per ogni aggiornamento a 30 minuti/eventi.
La durata è condizionata al raggiungimento quota entro la finestra; `null` non
viene convertito in zero. Input manuali fuori dal contratto del modello o fuori
distribuzione possono causare astensione.

## API

| Metodo | Percorso | Funzione |
|---|---|---|
| GET | `/v1/catalog` | Catalogo, depositi e soglie quota |
| GET | `/v1/model-quality` | Registro e rapporto storico M03, senza nuova valutazione |
| POST | `/v1/sessions` | Seed di sviluppo 0–3, profilo e modalità di previsione |
| GET / DELETE | `/v1/sessions/{id}` | Quattro viste allo stesso cutoff / chiusura |
| POST | `/v1/sessions/{id}/advance` | Avanzamento di 1–3600 s fino a 48 ore |
| POST | `/v1/sessions/{id}/missions` | Missione immediata, quantità e scadenza assoluta |
| POST | `/v1/sessions/{id}/decisions` | Approve/defer/reject su richiesta già osservata |
| POST | `/v1/sessions/{id}/cancellations` | Annullamento con motivo |

Esempio con server avviato:

```python
import requests

base = "http://127.0.0.1:8000/v1"
r = requests.post(base + "/sessions", json={}, timeout=120)
r.raise_for_status()
v = r.json()
r = requests.post(f"{base}/sessions/{v['session_id']}/missions", json={
    "command_id": "prima_missione", "expected_revision": v["revision"],
    "origin_id": "central-a", "destination_id": "local-a",
    "deadline_s": 86400, "quantities": {"food-small": 10}, "urgent": False,
}, timeout=120)
r.raise_for_status()
assert r.json()["missions"][0]["lines"][0]["minimum"] == 8
```

Ogni comando richiede `command_id` e `expected_revision`. Gli ultimi 16 comandi
conservano firma e risposta per retry identici. Una firma diversa o revisione
obsoleta restituisce 409. Un retry fuori cache conserva la vecchia revisione e
non riesegue l'operazione. Dopo un conflitto rileggere la sessione. La mutazione
viene commessa sotto lock solo dopo validazione e verifica degli invarianti.
Input non validi non lasciano riserve o missioni parziali; una violazione durante
l'esecuzione invalida la sessione e richiede di crearne un'altra. Gli errori di
servizio riportano `detail.field` e `detail.reason`; quelli di schema indicano la
posizione del campo tramite Pydantic/FastAPI. La UI usa un UUID per ogni invio.

## Separazione del futuro e limiti

Le risposte sono proiezioni esplicite, mai `warehouse.snapshot()` integrale.
Sono esclusi danni non ispezionati, esposizione latente al freddo, arrivi/quantità
effettivi di forniture future, orari campionati delle approvazioni, tempi futuri
di riparazione e richieste non ancora create. Gli storici filtrano campi interni.
Il cutoff dei fatti è distinto dall'istante delle stime e dal rapporto storico M03.

Sessioni in memoria, isolate tramite UUID: usare **un solo worker**. Stato perso
al riavvio, lock di processo, massimo 8 sessioni; la UI chiude la precedente quando
ne crea una nuova. Il limite di 200 missioni blocca nuovi inserimenti manuali;
la domanda generata è limitata a un giorno. Massimo 15 articoli e 1000 unità per
articolo per inserimento manuale. Orizzonte: 24 ore di generazione più 24 di
estensione. Decisioni automatiche disabilitate; incidenti/forniture sintetici.
A fine orizzonte le missioni aperte restano censurate. La UI inserisce un articolo
alla volta; l'API supporta missioni con più articoli. L'import con quarantena resta
nei contratti D01 e non è un nuovo modulo di caricamento nella UI.

Questo è il perimetro locale U01: R01 deve ancora confezionare installazione e
ripristino end-to-end; R02 aggiungerà autenticazione/ruoli, persistenza multiutente,
limiti online e hosting. Questo server di sviluppo è previsto su loopback.

## Verifica

```bash
python -m pytest -q tests/test_logistics_api.py tests/test_logistics_dashboard.py
python scripts/check_quality.py --report reports/quality-nuova-verifica
```

Il test Streamlit usa AppTest con il vero backend FastAPI in processo: quattro
schede, creazione missione, avanzamento, refresh e chiusura. I test API verificano
anche recuperi manuali, isolamento, retry, errori atomici, informazioni nascoste,
checksum, modalità sperimentale, scadenza e arresto.
