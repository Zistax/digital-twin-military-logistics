# Chiusura M03 — 15 ottobre 2026

**M03, quindicesima voce su 18, completata:** test indipendente, report,
criteri quantitativi, registro verificato, promozione manuale e rollback.
La chiusura del lavoro non equivale a promozione del modello: **il candidato
non supera l'ammissibilità tecnica e nessuna versione è attiva**.
Prossima voce: **U01 — API e quattro viste (16ª su 18)**.

## Congelamento e uso del test

Protocollo, criteri e baseline sono fissati prima di aprire le tabelle test,
con checksum in `freeze.json` e commit sul ramo M03 precedente all'apertura.
[Commit di congelamento prima del test](https://github.com/Zistax/digital-twin-military-logistics/commit/0fb19bfc55f9f0979bd1a67cc99ab51be58dea0a).

I modelli M01/M02 restano quelli pubblicati: nessun retraining, calibrazione
aggiuntiva, modifica di feature, soglie o selezione dopo il test.
Le baseline sono fit soltanto sul training, prima della valutazione.

Il registro `attempt.json` segna l'apertura; l'esecuzione rifiuta una seconda
valutazione accidentale o input congelati modificati. Il test D03 è ora
**consumato**. Una revisione guidata da questi risultati richiederà nuovi
gruppi di test; ripetere lo stesso controllo non crea nuova evidenza indipendente.

Verificati 18 run accettati in sei gruppi, 1644 missioni,
210287 snapshot nativi e 16535 snapshot rolling campionati.
Missioni censurate: 459 (27.92%).
Nessun overlap con training o calibrazione; SHA256 degli archivi, manifest
e quattro tabelle utilizzate verificati. Sampling M02 identico e indipendente
dai target: quattro hash minimi per missione/regime più il primo stato di fase.
I record del test non diventano dati di calibrazione o training.

## Prestazioni con la policy effettiva

Ogni missione ha peso uno per regime/target. Predizioni mancanti per astensione
non diventano errori nulli e non vengono nascoste nei denominatori di disponibilità.
I confronti appaiati usano gli stessi casi e baseline fissate prima del test.
CI percentile al 95% con 1000 ricampionamenti dei sei gruppi, mantenendo insieme
tre varianti e tutte le missioni del seed. Evidenza limitata a sei gruppi.

| Canale | Missioni | Snapshot | Brier oppure MAE minuti ↓ | Baseline sullo stesso insieme ↓ | CI 95% differenza candidato−baseline |
|---|---:|---:|---:|---:|---|
| initial_classification | 1629 | 1629 | 0.0736 | 0.1437 | [-0.0793; -0.0606] |
| initial_duration | 415 | 415 | 1914.0118 | 2829.5603 | [-1078.7277; -756.6276] |
| post_duration | 411 | 2452 | 964.4996 | 1484.1305 | [-634.8798; -408.7349] |
| pre_duration | 415 | 2219 | 1870.3269 | 2829.2707 | [-1119.4376; -839.0332] |
| rolling_classification | 1629 | 8492 | 0.0581 | 0.1437 | [-0.0941; -0.0769] |

La baseline di classificazione è la prevalenza; per durata è la mediana
dei completati tardivi, ponderata per missione. La baseline operativa iniziale
è confrontata separatamente, con numerosità del sottoinsieme disponibile.

| Classificazione | ROC-AUC | PR-AUC | ECE |
|---|---:|---:|---:|
| initial_classification | 0.9341 | 0.9851 | 0.0252 |
| rolling_classification | 0.9610 | 0.9915 | 0.0165 |

I JSON riportano anche i CI di Brier/MAE e copertura/ampiezza; ROC-AUC, PR-AUC
ed ECE sono descrittive. La differenza appaiata negativa favorisce il candidato.
Nessun indicatore viene tradotto in una promessa di affidabilità operativa.

## Diagnostica senza astensione

Questi valori mostrano anche i casi difficili rimossi dalla policy. Non sono
un modo per aggirare l'astensione nell'uso del modello.

| Canale grezzo, solo diagnostica | Missioni | Brier oppure MAE minuti | Baseline |
|---|---:|---:|---:|
| initial_classification | 1644 | 0.0740 | 0.1454 |
| initial_duration | 895 | 2116.3532 | 3019.0559 |
| post_duration | 889 | 1131.7813 | 1820.9246 |
| pre_duration | 895 | 2083.5096 | 3019.0937 |
| rolling_classification | 1644 | 0.0583 | 0.1454 |

Baseline operativa iniziale: Brier 0.1096.
Stima operativa disponibile per 129 completati tardivi
(14.41% dei casi di regressione): MAE operativo
3046.2 minuti, candidato grezzo sul medesimo sottoinsieme
2141.7 minuti.

## Intervalli condizionati e disponibilità

Intervalli nominali all'80%, calibrati soltanto nei sei gruppi di calibrazione
prima del test. Misure riferite ai completati tardivi previsti, non alle durate
censurate ignote o a tutta la popolazione.

| Durata | Copertura ponderata | Ampiezza media, minuti | Gruppi coperti simultaneamente |
|---|---:|---:|---:|
| initial_duration | 99.76% | 13576.5 | 83.33% |
| post_duration | 99.92% | 10530.2 | 66.67% |
| pre_duration | 99.76% | 13371.7 | 83.33% |

Copertura elevata e ampiezza molto larga non equivalgono a precisione utile.
La censura può sottorappresentare i ritardi più lunghi: il target rimane
condizionato a quota raggiunta nel periodo osservato, non ritardo medio di
tutte le missioni. Durate nulle imputate alle censurate: **zero**.

| Stadio | Probabilità disponibile | Durata con intervallo disponibile |
|---|---:|---:|
| initial | 99.09% | 41.67% |
| post | non pertinente | 36.13% |
| pre | 99.08% | 41.67% |

Disponibilità rolling ponderata per missione e comprensiva di casi censurati;
disponibilità iniziale su tutte le richieste. Dopo la scadenza non si produce
una probabilità del ritardo già accaduto: accumulato più residuo e relativi
limiti rimangono coerenti. Quote raggiunte/annullamenti fermano il servizio.

Profili, urgenza, refrigerato e fasi sono in `Segmenti_M03.csv` e nel JSON.
Segmenti con meno di cinque gruppi, classificazione con meno di 100 missioni
o 20 esempi per classe, oppure durata con meno di 30 completati previsti sono
segnalati come evidenza insufficiente. Non sono considerati promossi.

## Esito dei criteri P15

I criteri sono limiti tecnici provvisori per una demo sintetica, dichiarati
nel protocollo prima del test; non SLO concordati con un utilizzatore operativo.
Nessun requisito del test è stato ritoccato per ottenere un esito positivo.
Oltre al confronto statistico, si richiedono ECE ≤0,05, miglioramento MAE ≥10%,
MAE ≤1440 minuti, copertura individuale/simultanea ≥80%, ampiezza ≤2880 minuti,
probabilità disponibile ≥95% e durata con intervallo ≥50%.

Gate superati: 156 su 205;
gate non superati: 49. Esito: **non ammesso alla promozione**.

Criteri globali non superati:

- `frequency_validated_at_30_minutes`
- `initial_duration|duration_mae`
- `initial_duration|interval_width`
- `pre_duration|duration_mae`
- `pre_duration|interval_width`
- `post_duration|interval_width`
- `post_duration|interval_group_coverage`
- `initial|duration_availability`
- `pre|duration_availability`
- `post|duration_availability`

L'elenco completo, incluse insufficienze e fallimenti dei segmenti obbligatori,
è in `Gate_M03.csv`. Il candidato resta invariato; non si corregge sul test.

D03 ha snapshot orari. I test funzionali del servizio a 30 minuti/eventi/scadenza
non dimostrano copertura statistica per tutti quegli istanti. Il criterio di
frequenza rimane bloccante per una promozione senza restrizioni: occorrerà un
nuovo piano indipendente coerente con la frequenza di utilizzo.

## Registro, verifica e rollback

`models/registry-v1.json` conserva due versioni immutabili per checksum:
M01 iniziale e M02 che ne include la dipendenza. Stato `evaluated_not_eligible`,
puntatore attivo **nullo**. Sono conservati artefatti, protocolli, dati e ambiente
tramite riferimenti congelati, report e cronologia. Modelli originali preservati.

```bash
python scripts/model_registry.py inspect
python scripts/model_registry.py verify
```

Promozione e rollback sono disponibili come funzioni e CLI, ma non sono stati
eseguiti sui candidati reali. Richiedono un JSON di approvazione con consenso
esplicito, approvatore e motivazione; il gate negativo non è aggirabile con
l'approvazione. Il rollback accetta solo versioni già promosse e ancora integre.
I test verificano questi flussi su artefatti artificiali, senza attivare modelli reali.
L'assenza di una versione attiva non genera un fallback silenzioso.

U01 potrà presentare esplicitamente un candidato **sperimentale** per la demo,
distinguendolo da un modello promosso; non deve nascondere censura, astensione,
ampiezza o stato del gate.

## Riproduzione e integrità

Usare le dipendenze runtime e `requirements-m01.txt`. Preparare le tabelle
iniziali e il campione M02 come descritto nei relativi rapporti; modelli congelati
e quattro archivi D03 sono già pubblicati. Il valutatore verifica nuovamente i
checksum e non chiama il fit dei candidati nell'azione `evaluate`.

```bash
python scripts/evaluate_m03.py freeze --output reports/m03-verifica-identica
python scripts/evaluate_m03.py evaluate --archives /percorso/archivi --output reports/m03-verifica-identica
```

Solo in un checkout di riproduzione con registro separato, artefatti e protocollo
identici: è una verifica dello stesso esito, non un nuovo test indipendente.
Non usare queste istruzioni per selezionare nuove configurazioni sul vecchio test.
Il registro rifiuta la ridefinizione di una versione già registrata.

`test-predictions.jsonl.gz` conserva snapshot, truth separato e uscite/versioni;
il report collega gli esatti SHA256 dei candidati. Il freeze identifica sorgenti,
baseline, protocolli, piano/split, versioni e dati di sviluppo utilizzati.
L'audit di apertura e il risultato rimangono versionati.

**Qualità: 329 test e 16 sotto-test passati, Ruff e Black superati; copertura del nucleo 92.70%.**
La suite è stata completata a sorgenti fermi prima di aprire il test finale.
Dodici nuove regressioni includono metriche/pesi/bootstrap, gate negativi,
immutabilità, checksum, approvazione manuale, rollback e flusso completo su
fixture artificiale. Rimane l'avviso esterno Starlette/httpx.

M03 è chiusa come lavoro di valutazione e governo delle versioni. Promozione
non concessa; nessun risultato sintetico equivale a certificazione reale.

Dopo la suite completa, la prova del comando con output relativo ha individuato
un problema di normalizzazione dei percorsi: corretto prima di aprire il test,
con le 12 regressioni mirate ripassate e registrate in `additional_checks` del
rapporto di qualità. Nessun modello o criterio di valutazione è stato modificato.
