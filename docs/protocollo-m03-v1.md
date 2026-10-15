# M03 v1 — test finale e registro, 15 ottobre 2026

Protocollo fissato prima dell'apertura delle tabelle test. Origine:
commit `5183cbe2b7a23c8c4850ed746323b85f6af00914`.
Nessun nuovo training/calibratore o modifica del candidato dopo il test.
Il test D03 viene consumato per questa valutazione conclusiva, anche se negativa.
Una revisione del modello guidata dai risultati richiederà nuovi gruppi test.

## Candidati e baseline congelati

M01 iniziale e M02 rolling/intervalli sono gli artefatti già pubblicati: si
verificano SHA256 di modelli, protocolli e sorgenti M01/M02. Le sole nuove
baseline sono fit sul training prima del test: prevalenza, baseline operativa
iniziale, mediana dei completati tardivi; prevalenza/mediana ponderate rolling.
Nessuna soglia di allarme binaria derivata da quelle storiche del prototipo.

Test: 18 run accettati, sei gruppi di seed con le tre varianti indivisibili.
Checksum dei quattro archivi, manifest e quattro tabelle utilizzate verificati.
Rolling: identico campionamento M02 (quattro hash minimi e primo stato per
missione/regime), scelto prima di leggere i target. Le durate censurate restano
mancanti; classificazione delle censurate con ritardo noto ammessa.

Una missione pesa uno per regime/target incluso. Si valuta separatamente:
iniziale, rolling prima della scadenza, residuo dalla scadenza e fasi operative.
Confronti fra candidato e baseline sugli stessi casi, con numerosità/copertura
esplicite. Metriche su tutti i casi ammessi al target per il predittore grezzo,
oltre a quelle sulla policy effettiva con astensione. L'output grezzo è solo
diagnostico e non aggira la policy nell'uso del modello.

## Criteri P15 per ammissibilità tecnica

Questi sono limiti tecnici provvisori per una **demo sintetica**, non SLO
concordati con un utilizzatore operativo. Fissati usando solo evidenza precedente
M01/M02, prima del test; l'unità di un giorno riprende l'errore elevato già
riportato in M01. La promozione richiede comunque approvazione manuale distinta.

| Aspetto | Criterio obbligatorio |
|---|---|
| Integrità | Artefatti e dati verificati, sei gruppi test, nessun overlap training/calibrazione |
| Classificazione iniziale e rolling | Brier inferiore alla prevalenza, limite superiore CI 95% della differenza appaiata <0; ECE ≤0,05 |
| Durata per i tre momenti | Miglioramento MAE ≥10% rispetto alla mediana sullo stesso insieme, limite superiore CI della differenza <0, MAE ≤1440 minuti |
| Intervalli | Copertura ponderata ≥0,80, copertura simultanea dei gruppi ≥0,80, ampiezza media ≤2880 minuti |
| Disponibilità | Probabilità iniziale/pre ≥0,95; durata con intervallo ≥0,50 delle richieste, incluse quelle censurate nel denominatore |
| Segmenti obbligatori | Ogni profilo, urgenza e refrigerato: ≥5 gruppi; classificazione con ≥100 missioni previste e ≥20 esempi per classe; durata con ≥30 completati tardivi previsti |
| Qualità | Gate regressioni/lint/format e coverage nucleo ≥90% |
| Frequenza | D03 orario non valida da solo copertura a tutti gli istanti del servizio a 30 minuti: promozione senza restrizione di frequenza bloccata |

I segmenti sotto soglia sono **evidenza insufficiente**, non promossi per
assenza di errori. Per i segmenti sufficienti si applicano i medesimi criteri
puntuali di Brier/ECE, MAE/ampiezza/copertura; i CI appaiati sono riportati
globalmente. Fasi con dati insufficienti rimangono non validate.

CI percentile 95% con 1000 ricampionamenti dei sei gruppi di seed, mantenendo
insieme le tre varianti e tutte le missioni del gruppo. Si riportano ROC-AUC,
PR-AUC, Brier, ECE, MAE, errori oltre un giorno, copertura, ampiezza e quota di
richieste servite. Sei gruppi danno evidenza limitata: nessuna certificazione.

## Registro, approvazione e rollback

Versioni e dipendenze immutabili per SHA256: modello/configurazione, dati di
riferimento, protocollo, report, esito gate e ambiente. Un solo puntatore attivo,
inizialmente nullo. Un candidato che fallisce il gate resta valutato/non ammesso.
Il confronto non promuove automaticamente e non riaddestra il modello.

La funzione di promozione richiede gate superato e un atto esplicito con
approvatore e motivazione; verifica nuovamente checksum di modello e report.
Il rollback richiede lo stesso atto e una versione precedentemente attiva con
artefatti ancora integri. Registro con cronologia e scrittura atomica.
U01 potrà usare un candidato solo distinguendolo esplicitamente da un modello
promosso; l'assenza di un attivo non attiva silenziosamente un fallback.

## Chiusura M03

Report indipendente, limiti, gate anche negativo, registro e regressioni
permettono di chiudere M03. La chiusura del lavoro non equivale a promuovere il
candidato o raggiungere l'affidabilità del prodotto. Non si ritocca il modello
per far superare il test già consultato.
