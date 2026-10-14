# Protocollo D03 v1 — congelato prima delle estrazioni

Riferimento: Specifica Unificata v1, §14 e voce D03. Prerequisiti: pilota D02
validato e F01/F02/F03/D01 chiuse nel nucleo operativo. Il nuovo codice del lotto
viene verificato prima della produzione con l'intera suite e il gate qualità.

- 30 seed nuovi: **1000–1029**, ciascuno nei tre profili regular, pressure e
  perturbed. I seed di sviluppo 0/1/2/3 sono esclusi.
- Generazione per sette giorni, estensione massima di sette giorni; stesse
  policy del nucleo v1. Arresto al drenaggio delle missioni o al limite.
- Il gruppo indivisibile è `base-seed-N`, con tutte e tre le varianti e tutte le
  relative missioni/osservazioni.
- Ordinamento dei seed mediante SHA-256 di `d03-split-v1|seed`: i primi 18 gruppi
  sono training, i successivi 6 calibrazione, gli ultimi 6 test. L'assegnazione
  non dipende dagli esiti e viene salvata prima del primo run.
- Conteggi esatti: **54/18/18 simulazioni**, cioè **18/6/6 per profilo**. Tuning
  futuro interno al training, raggruppato almeno per seed; calibrazione e test
  non entrano nel tuning. Nessun modello viene addestrato in D03.

`plan.json` contiene gruppi, run, policy, timestamp e hash dei sorgenti; il piano
ha un checksum e non viene modificato durante l'esecuzione. Ogni simulazione ha
un identificativo distinto. Il grado di parallelismo è soltanto un parametro
di esecuzione; non cambia seed, gruppi o policy.

Ogni run esporta il bundle nativo v4 e viene riletto semanticamente; conserva
manifest, otto tabelle, contesto osservabile, registro e trace operativo. Il
checkpoint viene scritto solo dopo l'esito del controllo. Un run fallito resta
con la sua diagnosi; il riavvio usa lo stesso seed e un nuovo numero di tentativo,
senza sostituire il seed in funzione degli esiti. Un cambio dei sorgenti blocca
il riavvio del lotto: occorre una nuova versione/piano.

Alla fine vengono riletti tutti i 90 bundle e ricontrollati hash, configurazioni,
identità, conteggi, maschere training e trace. Si produce un manifest dei tre
insiemi con i riferimenti ai bundle e ai loro hash. Nessuna riga di simulazioni
invalide entra negli insiemi. Se manca un run valido il lotto non è completo.

Le distribuzioni pubblicate sono conteggi descrittivi per profilo/insieme,
non prestazioni predittive: missioni, quote raggiunte, censura, annullamenti,
puntualità, classe ignota e snapshot. Il test può essere consultato per integrità
e questi conteggi; non per scegliere modelli, parametri o soglie.

Non si impone un bilanciamento artificiale 50/50 o un numero esatto di missioni.
Le circa 8.400 missioni sono un'attesa, non un criterio per riscrivere le
estrazioni. Osservazioni della stessa missione sono dipendenti; i target nulli
restano nulli e le durate dei soli completati sono condizionate al completamento.
La valutazione predittiva e i relativi limiti quantitativi appartengono a M01–M03.

Riproduzione o ripresa, dalla radice del repository:

```bash
python -m src.logistics.batch reports/d03-batch-v1 --workers 6
```

Prima esecuzione: directory nuova. Ripresa: stesso piano e stessi sorgenti,
con rivalidazione dei checkpoint già presenti. Non usare due coordinatori
contemporaneamente sulla stessa directory.
