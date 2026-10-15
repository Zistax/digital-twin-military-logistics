# Chiusura M01 — 15 ottobre 2026

**M01, tredicesima voce su 18, completata nel perimetro della previsione iniziale.**
Pipeline riutilizzabile, confronto sui dati D03, probabilità calibrata,
ritardo condizionato e astensione sono implementati. Prossima voce: **M02**.

## Dati e separazione

4949 missioni da 54 simulazioni training, 18 gruppi di seed indivisibili.
Sei fold interni al training, con tre gruppi per fold e tutte le varianti
dello stesso seed nello stesso fold. Ogni missione pesa una volta.
1646 missioni da 18 simulazioni/6 gruppi riservate al solo fit sigmoidale.
**Zero tabelle del test finale lette**; nessuna scelta basata sul test.
Archivi, manifest, tabelle, righe e piano verificati; i retry accettati dal
catalogo D03 sono usati esplicitamente, senza assumere che il primo sia valido.

1450 missioni training sono censurate (29,30%). I loro ritardi noti sono
inclusi nella classificazione. La regressione utilizza soltanto i 2576 esiti
completati in ritardo: le durate censurate restano nulle nel registro e non
sono trasformate in zeri, né usate come esiti completati.

## Confronto interno al training

Metriche su predizioni fuori fold, prima della calibrazione finale:

| Classificatore | Brier ↓ | ROC-AUC ↑ | PR-AUC ↑ | ECE ↓ |
|---|---:|---:|---:|---:|
| prevalence | 0.1520 | 0.4576 | 0.7989 | 0.0002 |
| operational | 0.1148 | 0.7180 | 0.8874 | 0.0253 |
| logistic | 0.0864 | 0.9172 | 0.9794 | 0.0174 |
| boosting | 0.0820 | 0.9277 | 0.9827 | 0.0163 |

Il boosting è selezionato con il criterio Brier fissato nel protocollo;
CI bootstrap al 95% per gruppi: **0,0765–0,0880**. La sigmoide finale è
stimata soltanto sulla calibrazione; i suoi risultati sul medesimo insieme
non sono presentati come una verifica indipendente. Il miglioramento non
costituisce promozione o affidabilità operativa.

| Ritardo condizionato | N | MAE minuti ↓ | P90 errore assoluto |
|---|---:|---:|---:|
| operational | 348 | 2955.4 | 8298.7 |
| median | 2576 | 2889.7 | 5800.1 |
| boosting | 2576 | 2031.5 | 4646.6 |

La baseline operativa ha una stima per soli 348 dei 2576 casi (13,51%);
il confronto sullo stesso sottoinsieme dà MAE 2955,4 minuti per la baseline,
2944,3 per la mediana e 2082,6 per il boosting. La selezione tra i candidati
a copertura completa sceglie il boosting. CI bootstrap MAE 1914,0–2138,3 minuti.
Il target è la **mediana del ritardo dato esito tardivo completato**: non è
la durata totale, il ritardo medio della popolazione o una stima delle
missioni censurate. L'errore resta elevato: 33,86 ore medie assolute e il
51,51% dei casi supera un giorno di errore. La selezione non elimina questo limite.

## Segmenti e astensione

| Segmento training | Missioni | Censurate | Brier boosting | MAE completati tardivi, minuti |
|---|---:|---:|---:|---:|
| profile=perturbed | 1227 | 194 | 0.0899 | 1687.4 |
| profile=pressure | 2495 | 1109 | 0.0632 | 2432.8 |
| profile=regular | 1227 | 147 | 0.1124 | 1828.5 |
| urgent=0 | 3968 | 1444 | 0.0675 | 2309.4 |
| urgent=1 | 981 | 6 | 0.1406 | 1112.3 |
| cold=0 | 4100 | 1238 | 0.0830 | 1938.5 |
| cold=1 | 849 | 212 | 0.0774 | 2421.4 |

Il JSON contiene numerosità, CI per gruppi, errori elevati e sottoinsiemi comuni.
Il supporto è distinto per urgenza × refrigerato × disponibilità della stima;
meno di 30 esempi o tre gruppi causa astensione. La durata richiede inoltre
30 esiti tardivi completati in tre gruppi e censura non oltre il 40%.
Valori fuori dagli intervalli training, categorie non viste o osservazioni
non iniziali causano astensione. Le soglie sono guardie di supporto preventive,
non soglie quantitative di promozione M03.

Sulla calibrazione la pipeline restituisce 670 previsioni con durata
condizionata, 972 sole probabilità e 4 astensioni complete. Questi conteggi
misurano la disponibilità dell'uscita, non la sua accuratezza indipendente.
Ogni risposta include target, versione, dominio sintetico e motivi di astensione.
Intervalli, previsione rolling e residuo sono rinviati a M02.

## Riproduzione

Usare Python e le versioni indicate in `report.json`, dipendenze runtime
e `requirements-m01.txt`. Ricomporre i quattro ZIP dal ramo dati seguendo
`data/d03/README.md`; quindi, dalla radice:

```bash
python scripts/prepare_m01_data.py --archives /percorso/archivi --output reports/d03-batch-v1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python scripts/train_m01.py --dataset reports/d03-batch-v1 --output reports/m01-ripetizione
python scripts/predict_m01.py --model reports/m01-v1/initial_predictor.joblib --observation reports/m01-v1/example_observation.json
```

Lo script di preparazione verifica i quattro SHA256 pubblicati ed estrae solo
le tabelle iniziali di training/calibrazione; non richiede spazio per tutto
il dataset nativo. Il training registra protocollo e hash implementazione
prima del fit, salva predizioni fuori fold, provenienza, modello e checksum.
La CLI controlla il checksum del modello. Il roundtrip del modello persistito
è verificato contro le predizioni salvate. Il dominio fisico D03 non è stato
modificato; per rigenerare il lotto originale usare il commit D03 congelato,
senza riprendere quel lotto con sorgenti M01 aggiunti.

## Qualità e decisioni aperte

**288 test e 16 sotto-test passati; Ruff e Black passati; copertura del nucleo 91.87%.**
I 17 nuovi test M01 coprono fold per gruppi, esclusione delle feature future,
censura, input invalidi, astensione, serializzazione, retry accettati, checksum
e assenza delle directory di test. Sono stati verificati anche estrazione reale
dei 72 bundle e CLI. L'avviso di deprecazione Starlette/httpx resta esterno al progetto.

La prima esecuzione completa è conservata in `reports/quality-m01-20261015`:
fallì perché i sorgenti furono modificati durante il controllo di congelamento.
La verifica finale è stata ripetuta a codice fermo in
`reports/quality-m01-final-20261015`; non è stato allentato il controllo.

P03 è rispettato con target condizionato e censura esplicita. P06 non viene
aggirato: non entra una previsione meteo futura vera; la stima operativa è
quella osservabile del nucleo. P14 è deciso solo per la previsione iniziale
(mediana, candidati, calibrazione, supporto); rolling/residuo/intervalli restano
M02. P15 e promozione manuale restano M03. API e quattro viste restano U01.

I risultati derivano da dati sintetici; non equivalgono a validazione su
operazioni reali. Nessun modello è promosso automaticamente.
