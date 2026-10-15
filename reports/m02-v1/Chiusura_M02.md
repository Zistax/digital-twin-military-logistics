# Chiusura M02 — 15 ottobre 2026

**M02, quattordicesima voce su 18, completata nel perimetro implementativo
documentato.** Rolling pre-scadenza, residuo post-scadenza, intervalli iniziali
e rolling, pesi per missione, astensione e servizio di aggiornamento sono
implementati e verificati. Prossima voce: **M03 — test indipendente e registro**.
Nessuna promozione automatica e nessuna promessa di affidabilità operativa.

## Dati, cutoff e riproducibilità

829954 snapshot nativi di training/calibrazione verificati in streaming nei
72 bundle accettati D03, inclusi i retry validi. Archivi, manifest, tabelle,
conteggi e relazioni controllati. Nessuna tabella delle 18 simulazioni test
è stata letta. Il campione include **49492 snapshot training** e **16499 di
calibrazione**: quattro hash minimi per missione/regime, più il primo stato
di ogni fase. La scelta è indipendente dai target e conserva gli snapshot
osservabili nativi, senza ricostruire retrospettivamente lo stato.

Ogni missione pesa complessivamente uno in ogni regime/target incluso,
anche nel preprocessing, nella calibrazione e nelle metriche. Le tre varianti
di ogni seed restano nello stesso fold; i sei fold training contengono ciascuno
tre gruppi. Nessun seed, profilo sperimentale, ID o target entra nelle feature.
Le condizioni iniziali sono esplicitamente prefissate `initial_`; avanzamento,
deficit, riserve e perdite ispezionate sono correnti. Non entrano danni nascosti,
meteo futuro vero o durate future di guasti/approvazioni.

## Confronti interni al training

Predizioni fuori fold, antecedenti alla calibrazione finale; i bootstrap al
95% ricampionano 18 gruppi indivisibili di seed, 400 volte con seed fisso.

| Target | Candidato | Missioni | Snapshot | Brier oppure MAE minuti ↓ |
|---|---|---:|---:|---:|
| classification | prevalence | 4949 | 25927 | 0.1520 |
| classification | logistic | 4949 | 25927 | 0.0696 |
| classification | boosting | 4949 | 25927 | 0.0635 |
| pre | median | 2576 | 13365 | 2889.6902 |
| pre | boosting | 2576 | 13365 | 1983.6914 |
| post | median | 2544 | 15969 | 1743.6307 |
| post | boosting | 2544 | 15969 | 1111.5168 |

Il criterio predefinito seleziona boosting per i tre target. Brier rolling
0,0635 (CI 0,0586–0,0686); ROC-AUC 0,9567, PR-AUC 0,9898 ed ECE 0,0117.
MAE del ritardo condizionato 1983,7 minuti (CI 1860,7–2105,0); MAE residuo
1111,5 minuti (CI 1055,5–1173,1). Gli errori restano elevati: rispettivamente
33,06 e 18,53 ore. Errori oltre un giorno: 51,56% e 26,02%.

Il riferimento operativo iniziale rimane quello di M01, con i suoi limiti e
sottoinsiemi comuni; non viene presentato come nuova stima della flotta corrente.
Le coorti prima/dopo scadenza differiscono e non vanno confrontate come se
contenessero le stesse missioni e le stesse informazioni.

La sigmoide finale usa esclusivamente la calibrazione pre-scadenza, con pesi
per missione. Il suo fit non è una valutazione indipendente. I risultati per
profilo, urgenza, refrigerato e fase, con numerosità/avvisi, sono nel JSON e CSV.

## Intervalli e loro limiti

Obiettivo nominale **80%**. Punteggio massimo di errore assoluto per missione,
poi per gruppo di seed, sulle sole durate completate ammesse dalla policy.
Con sei gruppi di calibrazione il rango finito è sei: si usa il massimo dei
sei punteggi. Intervalli simmetrici troncati a zero, con raggi finali:

| Target | Gruppi calibrazione | Raggio, minuti |
|---|---:|---:|
| pre | 6 | 9821.7 |
| post | 6 | 8978.8 |
| initial | 6 | 10003.0 |

La verifica interna usa tre rotazioni disgiunte 6 gruppi fit / 6 calibrazione /
6 verifica, soltanto nel training, con ricetta boosting fissata prima degli
esiti rolling. Nessun gruppo di verifica è usato per fit o calibrazione nella
propria rotazione. Non è il test finale, né guida la scelta di iperparametri.

| Rotazione | Target | Missioni previste | Copertura ponderata | Ampiezza media, giorni | Gruppi coperti simultaneamente |
|---|---|---:|---:|---:|---:|
| 1 | initial | 309 | 100.00% | 9.18 | — |
| 1 | pre | 309 | 100.00% | 8.71 | 100.00% |
| 1 | post | 299 | 100.00% | 7.10 | 100.00% |
| 2 | initial | 402 | 99.75% | 10.05 | — |
| 2 | pre | 402 | 100.00% | 10.20 | 100.00% |
| 2 | post | 396 | 99.93% | 8.47 | 66.67% |
| 3 | initial | 402 | 100.00% | 10.13 | — |
| 3 | pre | 402 | 100.00% | 9.70 | 100.00% |
| 3 | post | 258 | 100.00% | 7.90 | 100.00% |

La copertura individuale elevata si accompagna a intervalli **molto larghi**:
non dimostra precisione utile. Nella seconda rotazione post-scadenza solo
4 gruppi su 6 sono coperti simultaneamente (66,67%): l'obiettivo nominale non
è confermato in ogni singola rotazione. Le metriche sul fit di calibrazione,
marcate nel JSON, non sono prove indipendenti. Nessuna soglia è stata ritoccata
dopo questi risultati. Con sei gruppi l'evidenza resta limitata.

Gli intervalli sono condizionati a esiti tardivi che raggiungono le quote nel
periodo osservato. Non includono una soluzione statistica per le durate censurate,
non garantiscono l'80% su dati reali, su ogni segmento o su istanti non campionati.

## Censura e quota di richieste servite

Le censurate con ritardo noto restano nella classificazione; durata mancante
mai imputata a zero. Per la durata: 30 missioni completate tardive in tre gruppi,
segmento con censura non oltre 40%. Supporto generale: 30 missioni/tre gruppi,
categorie e intervalli numerici training. Scenari fuori supporto causano astensione.

Sulla calibrazione, disponibilità ponderata per missione:

| Regime | Missioni | Snapshot | Probabilità | Durata con intervallo | Missioni censurate |
|---|---:|---:|---:|---:|---:|
| pre | 1646 | 8685 | 99.76% | 40.70% | 452 |
| post | 1323 | 7814 | 0.00% | 34.32% | 452 |

Queste percentuali misurano disponibilità, non accuratezza indipendente. Il
denominatore comprende anche casi difficili/censurati. Prima della scadenza
si distingue probabilità e ritardo condizionato; dalla scadenza la probabilità
è sempre omessa. Rimangono ritardo accumulato, residuo e intervallo pertinente.
Ritardo finale = accumulato + residuo; lo stesso vale per entrambi i limiti.
Le spiegazioni elencano fatti osservati (fase, deficit, avanzamento, perdite
ispezionate e recuperi), senza attribuire causalità ai fattori.

## Servizio di aggiornamento vivo

Il lotto storico D03 ha snapshot **orari**, come previsto dal suo runner:
non è stato modificato e non si fabbricano snapshot intermedi. Il nuovo
`ForecastSession` aggiunge un servizio separato con frequenza predefinita di
1800 secondi configurabili, controllo alla scadenza esatta e aggiornamento al
passo pubblico dopo cambiamenti osservabili. Eventi osservati di percorso,
approvazioni o disponibilità possono essere notificati dal chiamante dopo il batch.
Più notifiche allo stesso istante aggiornano un solo record con ID stabile.

Il servizio usa gli snapshot di consegne ispezionate, non eventi nascosti.
Registra osservazione, snapshot iniziale, trigger, istante, versione e SHA256
del modello; cessa le previsioni a quote raggiunte/annullamento. Test con il
simulatore reale verificano 650 secondi di scadenza non allineata al passo,
1800 secondi di periodicità, cambio fase, coalescenza, distacco dei dati e arresto.

Le metriche sopra restano riferite agli snapshot D03 campionati: il funzionamento
della nuova frequenza è testato, ma non è dimostrata copertura statistica a
ogni nuovo istante di previsione. Questa limitazione va mantenuta nel piano M03.
La UI/API e il collegamento end-to-end del prodotto rimangono U01.

## Riproduzione e artefatti

Installare dipendenze runtime e `requirements-m01.txt`; versioni nel JSON.
Il campione verificato è conservato in due parti binarie con SHA256 per parte
e dell'intero file. Per ricomporlo dopo il checkout:

```bash
python scripts/restore_m02_data.py --directory reports/m02-v1/data
```

Per ricostruire anche le tabelle iniziali dai quattro archivi D03, seguire
`data/d03/README.md` e usare `scripts/prepare_m01_data.py`. Poi:

```bash
python scripts/prepare_m02_data.py --archives /percorso/archivi --dataset reports/d03-batch-v1 --output reports/m02-ripetizione/data
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python scripts/train_m02.py --dataset reports/d03-batch-v1 --prepared reports/m02-ripetizione/data --initial reports/m01-v1/initial_predictor.joblib --output reports/m02-ripetizione
python scripts/predict_m02.py --model reports/m02-v1/rolling_predictor.joblib --request reports/m02-v1/example_inputs.json --example pre
python scripts/predict_m02.py --model reports/m02-v1/rolling_predictor.joblib --request reports/m02-v1/example_inputs.json --example post
```

La CLI accetta anche una richiesta con sola `creation` per M01 estesa con
intervallo iniziale. Modello M01 originale preservato; nuovo artefatto M02
separato e versionato. I JSONL gzip conservano predizioni fuori fold e snapshot
di calibrazione con checksum del modello. Checksum, protocollo e sorgenti sono
confrontati prima della chiusura; esempi CLI ricaricati e aritmetica verificati.

## Verifica e stato finale

**317 test e 16 sotto-test passati; Ruff e Black superati; copertura del nucleo 92.46%.**
29 nuovi test M02: cutoff, censura, pesi, fold, scalatura numericamente stabile,
rank degli intervalli, astensione, serializzazione, servizio vivo e ricomposizione
dei dati. Rimane l'avviso esterno Starlette/httpx. La scalatura ponderata è stata
corretta prima del fit finale: varianza a due passaggi evita cancellazione sulle
colonne costanti. Un'interruzione temporanea dell'ambiente non è stata considerata
una verifica superata. La suite finale è ripetuta a sorgenti fermi.

P14 è deciso per pipeline iniziale/rolling, residuo, mediana, pesi, calibrazione
e astensione documentate. P15 resta M03: test indipendente, soglie quantitative,
numerosità per segmenti, registro/versioni, approvazione e rollback. Nessun modello
è promosso. Intervalli larghi, errori elevati, censura e differenza di frequenza
rimangono limiti visibili del candidato da valutare.
