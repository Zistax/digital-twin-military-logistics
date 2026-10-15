# R01 — Pacchetto locale riproducibile

Pacchetto: `reports/r01-v1/digital-twin-local-r01.zip`, cartella interna
`digital-twin-local`. Sono inclusi codice, configurazioni, CLI, quattro viste,
modelli candidati, registro e rapporti necessari alla demo. Il manifest elenca
SHA256 dei file e payload storici esclusi. La demo non richiede i GB del dataset.

## Installazione e avvio

Versione verificata: **CPython 3.12, Linux x86_64**. Non occorre attivare
l'ambiente: usare direttamente il suo interprete. Servono Python 3.12, accesso
Internet per la prima installazione e spazio per ambiente/dipendenze. Le versioni
transitive sono bloccate in `requirements-local.txt`; le dipendenze dirette sono
in `requirements-local.in`. I modelli usano lo stack scientifico M01/M02 congelato.

Estrarre lo ZIP e aprire un terminale nella cartella `digital-twin-local`.

Linux/macOS, con Python 3.12 disponibile:

```bash
python3.12 scripts/setup_local.py
.venv/bin/python scripts/local_demo.py doctor
.venv/bin/python scripts/local_demo.py smoke
.venv/bin/python scripts/local_demo.py serve
```

Windows, con Python Launcher e Python 3.12 installati:

```powershell
py -3.12 scripts/setup_local.py
.venv\Scripts\python.exe scripts\local_demo.py doctor
.venv\Scripts\python.exe scripts\local_demo.py smoke
.venv\Scripts\python.exe scripts\local_demo.py serve
```

I comandi Windows/macOS sono predisposti, ma non sono stati eseguiti su quei
sistemi in questa chiusura. Python 3.13 non è la versione validata del pacchetto:
installare 3.12 accanto alle altre versioni. `setup_local.py` non cancella ambienti
esistenti e rifiuta come destinazione una cartella ordinaria già presente.

Aprire `http://127.0.0.1:8501`. API e OpenAPI: `http://127.0.0.1:8000/docs`.
`serve` avvia un worker API e Streamlit, attende che siano pronti e arresta
entrambi con Ctrl+C o se uno termina. Il bind è su loopback. Porte occupate
causano un errore prima di contattare un server estraneo. Porte alternative:

```bash
.venv/bin/python scripts/local_demo.py serve --api-port 8010 --ui-port 8510
```

L'URL API viene passato alla dashboard; la barra laterale permette comunque di
modificarlo. Le sessioni sono in memoria e si perdono allo spegnimento. Non sono
un archivio persistente delle decisioni.

## Verifica ripetibile

```bash
.venv/bin/python scripts/local_demo.py doctor --report reports/local-doctor.json
.venv/bin/python scripts/local_demo.py smoke --report reports/local-smoke.json
.venv/bin/python scripts/local_demo.py check-servers --report reports/local-servers.json
```

`doctor` controlla interprete, tutte le versioni del lock, checksum dei candidati
e riferimenti del registro, e ogni file del manifest se eseguito dal pacchetto.
File mancanti/modificati o dipendenze diverse fanno fallire il controllo.

`smoke` verifica missione nativa, quota, retry, previsione sperimentale a
scadenza/cadenza, annullamento/arresto, rifiuto del modello approvato assente e
recupero con approvazione manuale. Non modifica registro o artefatti.

`check-servers` avvia processi reali API/Streamlit e usa AppTest contro l'API HTTP
reale: abilita esplicitamente il candidato sperimentale, crea sessione e missione,
avanza, aggiorna e chiude; infine termina entrambi i processi. Il controllo può
impiegare alcuni secondi e non richiede un browser grafico. I rapporti del rilascio
sono in [reports/r01-v1](https://github.com/Zistax/digital-twin-military-logistics/tree/master/reports/r01-v1).

## Uso e sperimentazione

Per le quattro viste e i comandi API: [guida U01](api-ui-u01.md).
Il default non carica ML. L'opzione sperimentale mostra NON PROMOSSO; il registro
mantiene `active=null`. Nessuna installazione promuove modelli o riesegue il test
M03 già consumato. Le limitazioni statistiche rimangono visibili.

Esempio di previsione da snapshot pubblicato, dalla radice:

```bash
.venv/bin/python scripts/predict_m02.py --model reports/m02-v1/rolling_predictor.joblib --request reports/m02-v1/example_inputs.json --example pre
.venv/bin/python scripts/model_registry.py verify
```

Un piccolo esperimento nativo con soli seed di sviluppo:

```bash
.venv/bin/python -m src.logistics.pilot reports/pilota-locale --seeds 3 --days 1 --extension-days 1
```

Il pilota produce rapporti per tre profili; non è nuova validazione predittiva.
Per dati e training completi, seguire [ripristino D03](../data/d03/README.md),
[protocollo M01](protocollo-m01-v1.md) e [protocollo M02](protocollo-m02-v1.md).
Il refit M02 può ricampionare gli archivi con `prepare_m02_data.py`, come nella
chiusura M02; il ripristino delle parti campionate richiede invece le parti
pubblicate in `master/reports/m02-v1/data`, escluse dallo ZIP leggero.
Gli archivi voluminosi sono nel ramo `d03-dataset-v1`, separati dal pacchetto;
i relativi piani e script sono inclusi. Non usare il test finale già consumato
per scegliere nuovi parametri. Scrivere esperimenti e refit in nuove directory,
conservando candidati e rapporti pubblicati. Modificare file del manifest farà
fallire `doctor`: per sviluppare usare un clone della repository e ricreare il
pacchetto dopo le modifiche, senza alterare gli artefatti congelati.

## Installazione senza rete sulla macchina destinazione

Su una macchina con **stesso sistema operativo, architettura e Python 3.12**:

```bash
python3.12 -m pip download --only-binary=:all: -r requirements-local.txt --dest wheelhouse
python3.12 scripts/setup_local.py --wheelhouse wheelhouse
```

Trasferire pacchetto, Python già installato e wheelhouse alla macchina offline.
L'opzione usa `--no-index`; non costruisce estensioni da sorgenti. La chiusura
verifica l'installazione da rete/cache in ambiente nuovo; non certifica un
wheelhouse per sistemi diversi né un installer Python incorporato.

## Ricostruzione e controlli di sviluppo

```bash
python scripts/build_local_package.py --output reports/r01-v1/digital-twin-local-r01.zip --base-commit 44524aed6d65a1283639435ea44101c57554a303
python -m pip install -r requirements-local.txt -r requirements-quality.txt
python scripts/check_quality.py --report reports/quality-nuova-verifica
```

Il builder usa file ordinati, timestamp e permessi ZIP fissi; due build dallo
stesso contenuto e commit base producono gli stessi byte. `base_commit` indica
la base di lavoro, mentre l'identità esatta del contenuto è il manifest SHA256:
può includere modifiche di rilascio successive a quel commit. Il comando sopra
fissa la base del pacchetto pubblicato anche dopo nuovi commit della repository. Lo ZIP non include
ambienti virtuali, cache, credenziali o payload di training/inferenza voluminosi.

Per aggiornare le dipendenze, usare un nuovo ambiente 3.12 con
`requirements-local.in`, rigenerare il freeze, eseguire i controlli e costruire
un nuovo pacchetto. Non allentare automaticamente i vincoli dei modelli salvati.

R01 consegna la demo locale. **R02** resta distinta: autenticazione/ruoli,
persistenza multiutente, limiti online, hosting e pubblicazione.
