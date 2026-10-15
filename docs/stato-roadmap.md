# Stato della roadmap — 15 ottobre 2026

**Voci F01–M03 completate nei rispettivi perimetri documentati.** M03 è
la quindicesima voce su 18. La posizione non equivale a una percentuale del lavoro:
UI, packaging e pubblicazione restano da realizzare; il candidato non è promosso.

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
| **D03** | **Lotto da 90 simulazioni e split** | **Completato**: 90 run nativi verificati anche nell’audit finale, 30 gruppi indivisibili, split 54/18/18; 8239 missioni e 1040241 snapshot rolling; rapporto e catalogo prodotti |
| **M01** | **Baseline e previsione iniziale** | **Completato**: confronti training per gruppi, calibrazione separata, pipeline persistita e astensione; ritardo condizionato con limiti espliciti; test finale riservato a M03 |
| **M02** | **Previsioni aggiornate e incertezza** | **Completato nel perimetro documentato**: pesi per missione, rolling/residuo, intervalli per gruppi, astensione e servizio a 30 minuti/eventi/scadenza; limiti su censura, ampiezza e frequenza visibili |
| **M03** | **Test indipendente e registro modelli** | **Completato**: test consumato su sei gruppi, confronto e gate documentati, registro verificato, promozione manuale/rollback; candidati non ammessi e nessun attivo |
| U01 | API e quattro viste | Nuovo nucleo non ancora collegato; UI e flussi di approvazione da integrare |
| R01 | Pacchetto locale completo | Demo CLI disponibili; packaging end-to-end del prodotto ancora da fare |
| R02 | Demo online limitata | Da implementare, verificare e pubblicare |

## Prossimo lavoro

Il gate D02 è passato su nove run finali: 834 missioni, 598 quote raggiunte,
236 censurate; nessuna missione aperta senza motivo operativo. Il pilota ha
individuato e corretto un errore nel reintegro urgente; i casi sono stati rifatti.

[Rapporto di chiusura D02](../reports/d02-closeout-20261013/Chiusura_D02.md).

**D03 (12ª su 18) è completato**: 30 gruppi, 90 simulazioni native verificate
e split 54/18/18. I seed 1000–1029 sono distinti dai seed di sviluppo 0/1/2/3.
L’audit finale è passato su tutti i bundle.

[Rapporto di chiusura D03](../reports/d03-closeout-20261014/Chiusura_D03.md).

**M01 (13ª su 18) è completata**: [rapporto e riproduzione](../reports/m01-v1/Chiusura_M01.md).
**M02 (14ª su 18) è completata**: [rapporto e riproduzione](../reports/m02-v1/Chiusura_M02.md).
**M03 (15ª su 18) è completata**: [rapporto indipendente e registro](../reports/m03-v1/Chiusura_M03.md).
La prossima voce è **U01 (16ª su 18): API e quattro viste**.
Il test finale D03 è stato consumato in M03; modelli M01/M02 non promossi. Il ritardo condizionato
resta soggetto a censura ed errori elevati, esplicitati nel rapporto.

[Protocollo D03](protocollo-d03-v1.md) e [ripresa operativa](esecuzione-d03-risorse.md).
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
con soglia ≥90% del nucleo. I rapporti datati conservano le prove e lo stato al momento della chiusura.
