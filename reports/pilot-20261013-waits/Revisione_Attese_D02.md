# D02 — revisione delle attese del profilo sotto pressione

13 ottobre 2026. Seed 0, sette giorni di generazione più sette aggiuntivi.

La nuova diagnostica è stata verificata rieseguendo l'intero caso sotto
pressione. Tutte e sei le tabelle del pacchetto v3 coincidono con quelle del
primo pilota: osservazioni iniziali, etichette, osservazioni rolling, target
rolling, consegne e carichi. Anche il pacchetto nuovo supera la verifica.
L'instrumentazione non ha modificato richieste, scadenze o comportamento.

Esito confermato: 139 missioni, 84 quote raggiunte, 55 incomplete al limite
simulato di 14 giorni. La riesecuzione ha richiesto 222.6 secondi;
non è un nuovo seed indipendente e non viene conteggiata come tale.

## Attese dei fornitori

| Primo blocco operativo | Secondi cumulativi | Ore-fornitura cumulative |
|---|---:|---:|
| Deposito chiuso | 74028300 | 20563.4 |
| Banchine occupate | 29903257 | 8306.5 |
| Spazio non disponibile dopo i controlli precedenti | 0 | 0.0 |

Almeno 298 ordini hanno accumulato attesa. A fine simulazione ci sono 252
forniture chiuse e 105 ancora in attesa. Le durate sono sommate per ordine:
non rappresentano il tempo reale della simulazione, che ha ordini concorrenti.
Comprendono durate parziali di ordini ancora aperti e non sono medie finali.

Il contatore parte dall'arrivo effettivo e non include lo scarico attivo.
Se più condizioni bloccano l'ordine, viene registrato il primo controllo:
apertura, banchina, spazio. Lo zero della colonna spazio non dimostra che
ci fosse spazio libero durante gli intervalli già bloccati da altri motivi.

## Attese prima dell'assegnazione delle missioni

| Motivo operativo | Secondi cumulativi | Ore-missione cumulative |
|---|---:|---:|
| Scorte insufficienti | 41708953 | 11585.8 |
| Nessun piano fattibile con la flotta disponibile | 20222625 | 5617.4 |
| Trasferimento a vuoto all’origine | 466560 | 129.6 |

Al cutoff, 29 missioni hanno motivo `stock` e 18 motivo
`no_feasible_greedy_plan`. Quest'ultimo descrive l'euristica e la flotta
attualmente disponibile: non prova l'assenza di qualunque soluzione ottima.
Le altre tre missioni in stato waiting hanno già un viaggio in coda;
cinque missioni nello stato en_route attendono lo scarico.

Questi contatori non si sommano ai tempi delle code dei singoli viaggi,
perché possono sovrapporsi e rappresentano entità diverse. Le attese dei
recuperi richiedono ancora una diagnostica dedicata.

## Decisioni della revisione

- Mantenere per questo confronto gli stessi parametri, orizzonte e richieste.
  La censura resta un esito esplicito, non viene eliminata aumentando il limite.
- Prima di aumentare capacità o scorte, costruire casi controllati di
  competizione fra scarichi esterni e carichi/scarichi della flotta, verificando
  priorità, occupazione per deposito e ordini molto vecchi.
- Estendere lo stimatore osservabile della disponibilità di scorte e flotta.
  I dati del primo pilota mostrano uso frequente del budget di scadenza
  convenzionale; le nuove attese spiegano meglio quando tale stima si astiene.
- Ripetere poi su altri seed di base. La riesecuzione attuale verifica
  equivalenza, non misura variabilità statistica.

D02 resta aperto e D03 non è avviato. F02/F03 e le tracce complete D01 restano
requisiti da completare. Nessuna modifica automatica di parametri fisici.

## Evidenze

`wait-review.json` contiene KPI, motivi finali, contatori per ordine e risultati
del confronto tabella per tabella. La cartella `seed-0-pressure` contiene il
pacchetto v3 verificato. Quattro nuovi test coprono le attese e la loro
invarianza rispetto alla partizione del tempo. Totale: **199 test passati**.
