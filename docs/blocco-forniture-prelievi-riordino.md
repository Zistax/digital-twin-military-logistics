# Forniture esterne, prelievi locali e riordino — blocco completato

8 ottobre 2026. Implementazione: `SupplyWarehouse`, estensione del trasporto.
Riferimento: specifica unificata v1, sezioni 6 e 11.2.

## Funzioni consegnate

| Area | Comportamento |
|---|---|
| Ordini programmati | Quantità e arrivo attesi separati da quantità e arrivo effettivi |
| Disponibilità | Merce utilizzabile solo dopo scarico e controllo, non al semplice arrivo |
| Fornitore esterno | Usa le banchine del deposito senza impegnare i mezzi della flotta |
| Saturazione | Scarico parziale, residuo sul veicolo esterno, banchina liberata e nuovo accesso |
| Refrigerazione | Capacità e tempi refrigerati distinti, senza compensazione con lo spazio ordinario |
| Fornitura incompleta | Residuo non consegnato riconosciuto all'arrivo e tolto dall'atteso; ordine chiuso dopo lo scarico effettivo |
| Prelievi locali | Solo stock disponibile, mai riservato; parziali ammessi e residuo conservato |
| Priorità nuova merce | Urgenti → arretrati locali → ordinarie; riserve già esistenti protette salvo urgenti |
| Arretrati | Ordinamento per scadenza del prelievo e ID; richiesto, residuo, prelevato, attesa e fine registrati |
| Calendario locale | Nessun prelievo a deposito chiuso; arretrati ripresi alla riapertura |
| Generazione giornaliera | 10–30% della domanda prevista delle spedizioni per articolo, ceil, seed; richieste anche nei giorni chiusi |
| Riordino | Controllo periodico per deposito/articolo, considerando stock, domanda e arrivi aperti |
| Capacità | Ordine automatico limitato allo spazio previsto disponibile; limitazioni registrate |
| Integrità | Idempotenza, rollback e conservazione delle quantità continuano a valere |

## Uso

Dalla radice del repository, Python 3.11+, nessuna dipendenza aggiunta:

```bash
python -m src.logistics.supply_demo
python -m unittest tests.test_logistics_core tests.test_warehouse tests.test_operations tests.test_transport tests.test_supply -v
```

Comandi nuovi:

- `order_supply`: ordine programmato con esito sintetico configurabile.
- `local_request`: richiesta locale singola, immediata o futura.
- `schedule_local_days`: generazione riproducibile su un orizzonte esplicito.
- `configure_reorder`: regole e frequenza dei controlli automatici.
- `inventory_position`: posizione inventariale corrente, non disponibilità fisica.

Le regole sono `ReorderRule(daily_demand, trigger_days, target_days, lead_s)`.
Usare i parametri approvati: centrali 1,5/3 giorni e 86.400 secondi; locali
0,5/1 giorno e 43.200 secondi. `daily_demand` è la domanda totale prevista,
comprensiva dei prelievi locali, calcolata dai parametri, non dalle future
estrazioni casuali. Con prelievo uniforme 10–30%, il riferimento medio locale
è il 20% della domanda prevista delle spedizioni.

## Posizione inventariale e capacità

Formula implementativa:

`posizione = stock utilizzabile fisico + arrivi impegnati − domanda ancora da caricare − arretrati locali dovuti`

Lo stock fisico include la parte riservata. La domanda ancora da caricare
include le relative richieste: **la riserva non viene sottratta una seconda
volta**. Le quantità già caricate sono escluse dalla domanda all'origine.

Gli arrivi comprendono ordini esterni aperti e piani di trasporto interno
assegnati, al netto degli scarichi. Non si considerano garantite le missioni
in entrata ancora prive di un piano. Prima dell'arrivo esterno conta l'ordinato;
dopo l'arrivo conta il residuo effettivamente presente. Le quantità future
nascoste non modificano la posizione corrente.

Si ordina strettamente sotto soglia; quantità desiderata = ceil(livello
obiettivo − posizione). Il limite di capacità considera stock e arrivi
impegnati della stessa area ordinaria/refrigerata. Gli articoli sono trattati
in ordine stabile, non con ottimizzazione della distribuzione dello spazio.
Domanda prevista zero disabilita il riordino di quell'articolo.

Questa è una politica conservativa: conta anche arrivi aperti oltre il lead
time e può rinviare ordini quando lo spazio è attualmente impegnato, pur
potendo liberarsi in futuro. Le scorte desiderate non vengono ridotte
silenziosamente: le limitazioni sono nel registro. Da valutare nel pilota,
insieme alla cadenza tecnica iniziale di controllo di un'ora.

## Fornitori e calendario

I fornitori attendono e scaricano sulle stesse banchine della flotta. In questo
blocco le operazioni interne ammissibili sono valutate prima dei fornitori;
fra fornitori si usa arrivo effettivo e ID. È una scelta tecnica per P09,
non una priorità operativa reale: la possibile attesa prolungata dei fornitori
va misurata nel pilota.

Ogni accesso paga setup e tempi di movimentazione. L'ordine rimane aperto
finché la quantità arrivata non è stata scaricata. Una fornitura con zero unità
si chiude all'arrivo. I beni ancora sui veicoli dei fornitori sono fuori dal
bilancio fisico interno: entrano una volta sola, allo scarico accettato.

Le richieste locali giornaliere usano l'orario nominale di apertura minimo del
calendario anche nei giorni chiusi. Il seed è derivato da giorno e deposito,
indipendentemente dall'ordine di esecuzione. L'orizzonte è esplicito; non viene
avviato un generatore infinito. Se l'orario del primo giorno è già passato,
quel giorno viene saltato senza creare eventi retroattivi.

## Demo verificata

Depositi aperti 24/7 nella demo, configurazione ammessa dalla specifica.
Partenza senza stock, una missione da dieci unità e una richiesta locale da
cinque. Domanda prevista totale dieci unità/giorno; soglia locale 0,5 giorni,
obiettivo un giorno; lead time approvato di dodici ore.

| Fase | Esito |
|---|---|
| Primo controllo | Posizione −15; ordine unico da 25 unità |
| Dopo 12 ore | Arrivo del fornitore; merce ancora non disponibile |
| Dopo 12 ore e 20 minuti | Fine scarico; prelievo locale da 5 e riserva missione da 10 |
| Dopo 12 ore e 42 minuti | Missione consegnata e mezzo liberato |
| Fine demo | 10 unità nel deposito iniziale, 10 a destinazione, 5 consumate |

Bilancio: 25 ricevute = 10 + 10 in stock + 5 uscite per consumo.
Nessun ordine duplicato. Le durate della missione sono prodotte da banchine
e rete; nessun esito viene imposto manualmente.

## Verifiche e limiti

**90 test superati**, inclusi i 72 precedenti e 18 nuovi. Verificati:
forniture ritardate/parziali, deposito chiuso, scarico frazionato, priorità e
riserve, FIFO degli arretrati, domanda zero, limiti di capacità, ordini aperti,
assenza di doppio conteggio, weekend, riproducibilità, informazioni future,
coesistenza di banchine interne/esterne e flusso completo fino alla consegna.

`actual_s` e `actual_quantities` sono per ora input sintetici. Non vengono
ancora estratti automaticamente ritardi e incompletezze con le probabilità
dei tre profili: appartengono al prossimo blocco degli imprevisti.
Gli snapshot sono diagnostici e contengono anche configurazioni future;
non sono direttamente utilizzabili come feature operative/ML.

L'inizializzazione delle scorte da copertura prevista resta da collegare al
generatore completo degli scenari. La persistenza è in memoria; API, UI e ML
storici non sono ancora integrati. La suite storica API/ML e la copertura
globale del 90% non sono state verificate in questo ambiente.

## File

- `src/logistics/supply.py`: forniture, domanda locale e riordino.
- `src/logistics/supply_demo.py`: demo riproducibile.
- `tests/test_supply.py`: accettazione del blocco.
- `operations.py`: ordinamento deterministico degli eventi con identificativi
  di banchina interni ed esterni, preservando il comportamento precedente.

Prossimo blocco: imprevisti e recuperi — guasti, refrigerazione, danni e
approvazioni. Nessun push o deploy eseguito.

## Aggiornamento S05

Implementato il nucleo guasti/recuperi; sono documentati i casi residui:
[guasti e recuperi](blocco-guasti-recuperi.md).
Per il progetto completo vedere [stato della roadmap](stato-roadmap.md).
