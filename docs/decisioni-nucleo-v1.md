# Registro decisioni del nucleo v1 — 13 ottobre 2026

Questo registro congela le convenzioni tecniche effettivamente implementate nel
simulatore sintetico. Il riferimento funzionale resta la Specifica Unificata v1;
le convenzioni qui elencate non sono nuove approvazioni dell'utente né risultati
di validazione sul campo. F01 richiede la risoluzione di P01–P04; la selezione dei
modelli e le scelte del prodotto rimangono nelle rispettive fasi successive.

| Punto | Contratto operativo congelato |
|---|---|
| P01, tempo | Secondi interi non negativi dalla data iniziale UTC. Il motore visita ogni prossimo evento, anche fra tick; il cutoff include gli eventi osservati allo stesso secondo. Il raggiungimento alla scadenza è puntuale. |
| P01, simultaneità | I completamenti già pianificati sono elaborati prima di un nuovo comando. I nuovi ingressi allo stesso istante non avviano il dispatch finché non viene richiesto `advance`. Il runner conserva l'ordine delle richieste; i conflitti operativi seguono gli ordinamenti deterministici del motore. Il registro aggiunge un ordinale `state:N`: ogni osservazione fa riferimento all'ordinale preciso, non soltanto al timestamp. |
| P01, fasi interne | `EnvironmentWarehouse._finish` aggiorna l'ambiente, poi la catena Recovery → Incidents → Supply → Transport → Operations processa recuperi, guasti, forniture, movimentazioni e uscite dagli archi. Segue il dispatch, poi la verifica degli invarianti e la registrazione. Le sottoclassi chiamano `super` nei punti definiti dal codice versionato nel manifest. Gli intervalli vengono accumulati prima del prossimo evento. |
| P02 | Per ciascun articolo, D_i(t) è la somma delle quantità utilizzabili delle consegne ispezionate e osservate entro t. Le quote sono arrotondate per eccesso. Obiettivo raggiunto, viaggio terminato e chiusura logistica sono distinti. Merce inutilizzabile non contribuisce; dopo l'accettazione non viene introdotto un nuovo evento retroattivo di danno. |
| P03 | Annullamenti esclusi dai target. Incompleti prima della scadenza: classe sconosciuta; oltre la scadenza: ritardo noto, durata ancora nulla e censurata. La regressione del ritardo condizionato usa solo completati in ritardo. Dopo la scadenza il rolling predice la durata residua, senza classificatore banale. Le maschere sono eseguibili in `training_masks.py`. |
| P03, bias | Le durate dei soli completati non stimano la media dell'intera popolazione. Riportare numero e quota di censurati per gruppo/segmento; nessuna sostituzione con zero. Scelta di modelli di sopravvivenza, calibrazione e soglie di promozione rinviata a M01–M03. |
| P04 | Identità composta simulazione/missione/viaggio/lotto/articolo. Carichi, scissioni e consegne hanno registri separati; trasferimenti conservano la genealogia, l'esposizione cumulativa al freddo e le quantità. Per una scissione danneggiata si trasferiscono prima le unità danneggiate: convenzione sintetica esplicita. Le riserve sono vincoli sullo stock, non nuove quantità fisiche. |

## Convenzioni già implementate e limiti

P05–P13 usano rete e capacità esplicite, traffico autocorrelato per gruppi, meteo
globale e forecast osservabile imperfetto. I flussi casuali indipendenti sono
derivati dai seed; i profili regular e perturbed condividono le richieste.
L'allocazione/packing è greedy e deterministica, senza prova di ottimalità. I
recuperi possono essere frazionati e riutilizzare un mezzo piccolo. Le forniture
esterne entrano nel bilancio fisico all'accettazione dello scarico; eventuali
residui attendono calendario, spazio e banchina. Riordino, prelievi, distribuzioni
e calendario sono definiti dai moduli e dai parametri del manifest.

La prima stima usa soltanto stock e flotta osservabili; quando indisponibile
rimane esplicitamente indisponibile. L'allowance del runner di 24 ore definisce
una scadenza sintetica, senza diventare una stima inventata. Dopo la generazione
si prosegue fino al drenaggio delle missioni o al limite di estensione: le sole
attività di fondo non impediscono l'arresto.

P19: gli annullamenti e la destinazione del carico seguono le operazioni del
nucleo; pausa interattiva e attesa umana effettiva restano U01. P20: non si
aggiungono guasti frigoriferi dei depositi o danni ulteriori dopo l'accettazione.
Sono limiti del modello corrente; un'estensione richiede una scelta esplicita.
P14–P15 e P17–P18 restano rispettivamente M01–M03 e U01/R01/R02.

## Contratti persistenti e migrazione — P16

Bundle nativo v4: otto tabelle JSONL più `manifest.json`. Quantità in unità
intere; tempo in secondi UTC; misure fisiche in kg/m³, serializzate come decimali
nel catalogo; ritardi e target in minuti. Durata ignota è `null`.

| Tabella | Identità / funzione |
|---|---|
| observations | Simulazione + missione; feature creation-v1 prima dell'ammissione |
| labels | Simulazione + missione; esito separato e cutoff comune |
| rolling_observations | Simulazione + osservazione; snapshot rolling-v1 dal vivo |
| rolling_targets | Simulazione + osservazione; target, censura e peso 1/N |
| delivery_events | Evento ispezionato; credito effettivo della quota |
| cargo_events | Carico/scissione; genealogia e conservazione dei lotti |
| operational_events | Simulazione + ordinale; cambiamenti di stock, riserve, flotta, code, operazioni, forniture, incidenti, ambiente e rete |
| planning_contexts | Simulazione + osservazione; stock, disponibilità, calendari, flotta e forniture osservabili, collegati all'ordinale |

Il manifest conserva configurazione effettiva, catalogo, rete, policy, stato
iniziale, comandi iniziali, versioni e hash dei sorgenti. È metadato per replay,
escluso dalle feature: può contenere la configurazione sintetica delle future
forniture. Il contesto osservabile, invece, non espone l'esito futuro.

Il lettore rifiuta checksum/count incoerenti, symlink, identità duplicate,
orfani, target inventati, cutoff incoerenti, violazioni di conservazione e
contesti diversi dallo stato del registro. I checksum garantiscono integrità
rispetto al manifest fornito, non autenticità crittografica del produttore.
Gli identificativi sono univoci nel rispettivo contratto e nella simulazione;
i retry esatti dei comandi sono idempotenti, quelli confliggenti sono respinti
con rollback anche del registro.

Migrazione: v3 resta leggibile come formato storico a sei tabelle, senza
attribuirgli configurazione o eventi mancanti. Per ottenere v4 si rigenera la
simulazione con il nuovo esportatore. v1/v2 e versioni sconosciute sono respinte;
nessun aggiornamento automatico inventa una storia mancante.

L'importazione di ogni tabella è validata contro un bundle correlato già
verificato. Duplicati esatti deduplicati; conflitti critici bloccanti. Righe
malformate conservate in quarantena con numero e motivo; oltre lo 0,5% il lotto
è respinto. Anche sotto soglia, relazioni o campi critici incoerenti bloccano
l'importazione senza risultato parziale. Non è un database o una UI completa.
