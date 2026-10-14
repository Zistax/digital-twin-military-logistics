# Stato della roadmap — 13 ottobre 2026

**Voci F01–D02 completate nel perimetro del nucleo operativo v1.** D02 è
l’undicesima voce su 18. La posizione non equivale a una percentuale del lavoro:
modelli predittivi, UI, packaging e pubblicazione restano da realizzare.

Sono stati prodotti sei incrementi operativi e avviato il generatore scenari: missioni; scorte/carico;
calendari/scarico; trasporto; forniture/riordino; guasti/recuperi.
La suite completa e i controlli lint/format sono verificati nel rapporto di
chiusura delle fondamenta. Sono implementazioni locali, non una prima versione
completa del prodotto.

| Voce | Blocco | Stato verificato |
|---|---|---|
| F01 | Requisiti e decisioni tecniche | Completato: registro congelato del nucleo; P01–P04 risolti, decisioni delle fasi future esplicitamente separate |
| F02 | Regressioni storiche e qualità | Completato: regressioni 60/10, 125/10 e tick finale, output univoci, CLI/API, lint/format reali e gate coverage ≥90% |
| F03 | Contratti, configurazioni e identificativi | Completato: bundle v4, manifest effettivo, identificativi, cutoff, relazioni, checksum e politica di migrazione v3 esplicita |
| S01 | Catalogo, missioni, quote ed esiti | Nucleo e catalogo completo collegati al generatore e testati |
| S02 | Depositi, stock, riserve, calendari e banchine | Nucleo implementato e testato |
| S03 | Flotta, viaggi e rete | Nucleo implementato e testato; packing euristico, limiti documentati |
| S04 | Forniture, prelievi e riordino | Nucleo e inizializzazione delle scorte collegati agli scenari e testati |
| S05 | Guasti, danni, freddo, recuperi | Perimetro funzionale implementato e testato, compresi guasti del soccorritore e recuperi frazionati; limiti sperimentali documentati |
| S06 | Generazione profili e arresto esperimenti | Integrato e verificato nel pilota: catalogo, richieste, inizializzazione, traffico/meteo, forecast e forniture stocastiche implementati; runner, prima stima osservabile, convenzione per stime indisponibili e arresto integrati; pilota operativo D02 eseguito; validazione statistica/predittiva nelle fasi successive |
| **D01** | **Eventi, dataset e KPI** | **Completato per il nucleo v1**: otto tabelle, replay operativo, genealogia, contesti osservabili collegati agli ordinali, KPI, import di tutti i contratti con quarantena e blocco critico |
| **D02** | **Pilota e revisione parametri** | **Completato per il nuovo nucleo operativo**: nove run finali validi sui seed 0/1/2, attese spiegate, errore nel reintegro urgente corretto, gate passato; limiti e decisioni documentati |
| D03 | Lotto da 90 simulazioni e split | Da eseguire, dopo il pilota |
| M01 | Baseline e previsione iniziale | Da implementare sul nuovo target |
| M02 | Previsioni aggiornate e incertezza | Da implementare |
| M03 | Test indipendente e registro modelli | Da implementare/verificare |
| U01 | API e quattro viste | Nuovo nucleo non ancora collegato; UI e flussi di approvazione da integrare |
| R01 | Pacchetto locale completo | Demo CLI disponibili; packaging end-to-end del prodotto ancora da fare |
| R02 | Demo online limitata | Da implementare, verificare e pubblicare |

## Prossimo lavoro

Il gate D02 è passato su nove run finali: 834 missioni, 598 quote raggiunte,
236 censurate; nessuna missione aperta senza motivo operativo. Il pilota ha
individuato e corretto un errore nel reintegro urgente; i casi sono stati rifatti.

[Rapporto di chiusura D02](../reports/d02-closeout-20261013/Chiusura_D02.md).

La prossima voce è **D03 (12ª su 18)**. Il lotto da 90 simulazioni non è stato
avviato in questa chiusura: servono il protocollo di generazione/split per gruppi
e seed distinti da sviluppo. I seed 0/1/2/3 sono di sviluppo, non test finale.
Il gate storico D02 mantiene il proprio stato e i propri limiti: i nove run v3
non vengono riscritti né presentati come run v4.

## Evidenza riproducibile

[Decisioni e contratti congelati](decisioni-nucleo-v1.md).
[Chiusura F01/F02/F03/D01](../reports/foundation-closeout-20261013/Chiusura_Fondamenta.md).

Dalla radice, dopo avere installato le dipendenze runtime e quelle di qualità:

```bash
python scripts/check_quality.py --report reports/quality-nuova-verifica
```

Il controllo usa una directory isolata e non modifica il CSV di audit o la
coverage preesistenti. Esegue Ruff, Black, l’intera suite e coverage misurata,
con soglia ≥90% del nucleo. Le modifiche sono locali, non inviate a GitHub.
