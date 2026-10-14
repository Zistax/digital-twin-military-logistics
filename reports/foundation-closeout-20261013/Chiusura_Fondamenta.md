# Chiusura F01, F02, F03 e D01 — 13 ottobre 2026

Le voci precedenti a D02 sono completate nel perimetro del nucleo operativo v1.
La roadmap è arrivata a **D02, undicesima voce su 18**, con F01–D01 ora chiuse.
La prossima voce è D03; il lotto da 90 simulazioni non è stato avviato.

| Voce | Risultato verificabile |
|---|---|
| F01 | Registro delle convenzioni tecniche congelato; ordine temporale, stati, quote, annullamenti, censura e genealogia espliciti; maschere training eseguibili |
| F02 | Prototipo corretto per 60/10, 125/10 e ultimo tick parziale; progresso finale esatto; output distinti senza sovrascrittura; configurazioni/input YAML, CLI e API verificati; lint e format realmente eseguiti |
| F03 | Manifest della configurazione effettiva e hash dei sorgenti; schema persistente v4, unità/nullabilità/identità e cutoff; validatori e politica di migrazione esplicita |
| D01 | Otto tabelle, replay operativo con conservazione, consegne/genealogia, feature e contesti osservabili, KPI e target separati; importazione di tutti i contratti con quarantena e blocco critico |

## Verifica finale

- **254 test passati**, più 16 subtest; nessun fallimento.
- Ruff: passato. Black: 94 file controllati, nessuna modifica necessaria.
- Coverage nucleo: **91,97%**, superiore al gate 90%.
- Coverage di tutto `src`, inclusa la UI storica: **90,66%**.
- Una segnalazione di deprecazione proviene da Starlette/httpx; non è un
  fallimento applicativo. La nuova UI resta una fase successiva.
- Controlli eseguiti in una directory temporanea isolata, preservando il CSV
  di audit e il file coverage preesistenti nel repository.

[Risultati e comandi esatti](../foundation-quality-verified/quality.json).
[Coverage per file e righe](../foundation-quality-verified/coverage.json).
[Decisioni, contratti e migrazione](../../docs/decisioni-nucleo-v1.md).

Il nuovo controllo incrociato dei contesti ha individuato una differenza fra
chiavi numeriche del traffico in memoria e chiavi stringa in JSON. Il formato è
stato uniformato, aggiunto un test end-to-end e ripetute le tre prove. Il primo
tentativo resta conservato in `foundation-native-v4`; i risultati validi sono
in `foundation-native-v4-final`.

## Prove native del formato v4

Seed 3 di sviluppo, un giorno di generazione e un giorno di estensione. Ogni
run esporta e rilegge il bundle, verificando manifest, checksum, relazioni,
genealogia, conservazione fisica, timestamp UTC e contesti collegati al registro.

| Profilo | Missioni | Quote raggiunte | Censurate | Snapshot rolling | Run valido |
|---|---:|---:|---:|---:|---|
| regular | 9 | 6 | 3 | 213 | Sì |
| pressure | 17 | 8 | 9 | 475 | Sì |
| perturbed | 9 | 4 | 5 | 240 | Sì |

[Report dei tre run](../foundation-native-v4-final/pilot.json).

Queste sono prove del contratto e dell'integrazione, non un nuovo pilota
statistico da 7+7 giorni. D02 resta documentato dal precedente pilota a nove
run sui seed 0/1/2, con 834 missioni. I suoi artefatti storici v3 e i relativi
limiti non sono riscritti né convertiti artificialmente in v4. Tutti e nove i
bundle storici v3 sono stati riletti e verificati con il nuovo lettore.

## Riproduzione e limiti

Installare le dipendenze runtime e `requirements-quality.txt`, poi eseguire:

```bash
python scripts/check_quality.py --report reports/quality-nuova-verifica
python -m src.logistics.pilot reports/prova-v4-nuova --seeds 3 --days 1 --extension-days 1
```

Le directory di destinazione devono essere nuove. I seed 0/1/2/3 sono di
sviluppo e non devono diventare il test indipendente. Il registro conserva gli
stati osservabili; i manifest di configurazione sono metadati di replay,
esclusi dalle feature. I checksum non autenticano il produttore e non provano la genuinità di una
fonte esterna.

Le durate dei completati restano condizionate al completamento; i censurati non
diventano durate zero. Nessuna misura di qualità predittiva è stata prodotta.
La chiusura delle fondamenta non completa M01–M03, U01 o R01–R02. Le modifiche
restano locali, senza commit, invio a GitHub o pubblicazione.
