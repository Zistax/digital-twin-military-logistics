# Fase 21 – Performance baseline & SLO (Parte 2, Giorni 4–6, Windows)

> **Obiettivo pratico (Parte 2)**  
> Collegare le statistiche di latenza a dei **SLO espliciti** e completare il quadro:
>
> - definire una piccola config SLO (`conf/ops/slo.yml`),
> - creare uno script `check_slo.py` che confronta media/p95 con le soglie,
> - aggiungere un test minimo sulla logica di parsing,
> - documentare il tutto nel `README.md`.


---

## Struttura Fase 21 – Parte 2

- **Giorno 4** – Definire gli SLO in `conf/ops/slo.yml` + script `check_slo.py`
- **Giorno 5** – Test automatici su parsing e percentile
- **Giorno 6** – Sezione “Performance & SLO” nel README + giro completo


---

## Giorno 4 – Configurare SLO e creare `check_slo.py`

### Obiettivo del giorno
- Creare un file di configurazione SLO,
- scrivere uno script che:
  - legge `logs/api/api.log`,
  - calcola media/p95 per endpoint con le funzioni esistenti,
  - confronta con gli SLO e segnala se sono rispettati.


---

### 1. Creare la cartella `conf/ops`

1. In **VS Code** o Esplora File, nella root del progetto, crea (se non esiste già) la cartella:

   - `conf`
   - dentro di essa: `ops`

Da terminale:

```bash
mkdir conf
mkdir conf\ops
```

**Checklist**
- [ ] Esiste `conf/ops`


---

### 2. Creare il file `conf\ops\slo.yml`

1. Dentro `conf/ops`, crea il file:

   - `slo.yml`

2. Inserisci una config semplice, ad esempio:

```yaml
api_latency_ms:
  # SLO di esempio per tempi di risposta
  p95_overall: 600    # p95 globale sotto 600 ms
  p95_health: 200     # /health deve rispondere molto velocemente
  p95_predict: 600    # /predict sotto 600 ms (esempio dal summary progetto)
```

3. Salva il file.

> Puoi adattare questi valori in futuro in base alle misure reali.

**Checklist**
- [ ] Esiste `conf/ops/slo.yml` con gli SLO base


---

### 3. Verificare la presenza di `pyyaml` nei requirements

1. Apri `requirements.txt` e verifica che sia presente:

```txt
pyyaml
```

Se non c’è, aggiungilo, salva il file e poi:

```bash
pip install -r requirements.txt
```

**Checklist**
- [ ] `pyyaml` è nei requirements e installato


---

### 4. Creare `src\tools\check_slo.py`

1. In **VS Code**, nella cartella `src\tools`, crea il file:

   - `check_slo.py`

2. Inserisci il seguente codice:

```python
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import yaml

from src.tools.api_latency_stats import load_latencies, summarize_latencies


SLO_CONFIG_PATH = Path("conf") / "ops" / "slo.yml"


def load_slo_config(path: Path = SLO_CONFIG_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File SLO non trovato: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data


def check_slo(
    log_path: Path | None = None,
    slo_path: Path = SLO_CONFIG_PATH,
) -> int:
    """Confronta le statistiche di latenza con gli SLO configurati.

    Ritorna 0 se tutti gli SLO sono rispettati, 1 altrimenti.
    """
    from pathlib import Path as _Path

    lp = _Path(log_path) if log_path is not None else Path("logs") / "api" / "api.log"

    latencies = load_latencies(lp)
    if not latencies:
        print(f"Nessuna latenza trovata nel log {lp}. Impossibile verificare SLO.")
        return 1

    summary = summarize_latencies(latencies)
    slo_cfg = load_slo_config(slo_path)

    api_slo = slo_cfg.get("api_latency_ms", {})

    p95_overall = float(api_slo.get("p95_overall", 600.0))
    p95_health = float(api_slo.get("p95_health", 200.0))
    p95_predict = float(api_slo.get("p95_predict", 600.0))

    print(f"Uso file di log: {lp}")
    print(f"Uso config SLO : {slo_path}")
    print()

    # Calcoliamo un p95 "globale" mettendo insieme tutte le richieste
    all_p95_values = [stats["p95_ms"] for stats in summary.values() if "p95_ms" in stats]
    p95_global = max(all_p95_values) if all_p95_values else 0.0

    exit_code = 0

    print("=== Verifica SLO latenze API ===")
    print(f"SLO p95_overall <= {p95_overall:.2f} ms  | misurato: {p95_global:.2f} ms")

    if p95_global > p95_overall:
        print(">> SLO globale NON rispettato.")
        exit_code = 1
    else:
        print(">> SLO globale OK.")

    # Controllo /health
    health_stats = summary.get("/health")
    if health_stats:
        p95_h = health_stats["p95_ms"]
        print(f"SLO /health p95 <= {p95_health:.2f} ms  | misurato: {p95_h:.2f} ms")
        if p95_h > p95_health:
            print(">> SLO /health NON rispettato.")
            exit_code = 1
        else:
            print(">> SLO /health OK.")
    else:
        print(">> Nessun dato per /health nel log.")

    # Controllo /predict (se presente)
    predict_stats = summary.get("/predict")
    if predict_stats:
        p95_p = predict_stats["p95_ms"]
        print(f"SLO /predict p95 <= {p95_predict:.2f} ms  | misurato: {p95_p:.2f} ms")
        if p95_p > p95_predict:
            print(">> SLO /predict NON rispettato.")
            exit_code = 1
        else:
            print(">> SLO /predict OK.")
    else:
        print(">> Nessun dato per /predict nel log.")

    return exit_code


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Verifica SLO di latenza API.")
    parser.add_argument(
        "--log-path",
        type=str,
        default=None,
        help="Percorso del file di log API (default: logs/api/api.log)",
    )
    parser.add_argument(
        "--slo-path",
        type=str,
        default=str(SLO_CONFIG_PATH),
        help="Percorso del file SLO YAML (default: conf/ops/slo.yml)",
    )

    args = parser.parse_args()

    log_path = Path(args.log_path) if args.log_path else None
    slo_path = Path(args.slo_path)

    exit_code = check_slo(log_path=log_path, slo_path=slo_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/tools/check_slo.py` con `check_slo` e `main()`
- [ ] `conf/ops/slo.yml` viene letto correttamente da `load_slo_config`


---

### 5. Prova pratica di `check_slo`

1. Assicurati di aver generato un po’ di log (usando `load_test_api` e qualche chiamata a `/predict`).  
2. Nel terminale (con `.venv` attivo), lancia:

```bash
python -m src.tools.check_slo
```

3. Dovresti vedere un output che confronta i p95 misurati con gli SLO configurati.

**Checklist (fine Giorno 4)**
- [ ] `check_slo` gira senza errori e stampa lo stato degli SLO
- [ ] In caso di violazione degli SLO, lo script lo segnala chiaramente


---

## Giorno 5 – Test automatici su parsing e percentile

### Obiettivo del giorno
- Aggiungere qualche test per la parte di **parsing log** e per la funzione `percentile`.


---

### 1. Test per `parse_latency_line` e `percentile`

1. In **VS Code**, nella cartella `tests`, crea il file:

   - `test_api_latency_stats.py`

2. Inserisci questo contenuto:

```python
from src.tools.api_latency_stats import parse_latency_line, percentile


def test_parse_latency_line_valid():
    line = "2025-11-16 14:10:12,345 [INFO] api - HTTP GET /health completed in 5.23 ms"
    parsed = parse_latency_line(line)
    assert parsed is not None
    path, ms = parsed
    assert path == "/health"
    assert abs(ms - 5.23) < 1e-6


def test_parse_latency_line_invalid():
    line = "2025-11-16 14:10:12,345 [INFO] api - qualcosa di diverso"
    parsed = parse_latency_line(line)
    assert parsed is None


def test_percentile_basic():
    values = [1, 2, 3, 4, 5]
    p50 = percentile(values, 50)
    p95 = percentile(values, 95)

    assert 2.0 <= p50 <= 4.0
    assert p95 >= 4.0
```

3. Salva il file.

**Checklist**
- [ ] Esiste `tests/test_api_latency_stats.py` con test su parsing e percentile


---

### 2. Eseguire i test

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest tests/test_api_latency_stats.py
```

Oppure, per tutta la suite:

```bash
pytest
```

Assicurati che tutti i test passino.

**Checklist (fine Giorno 5)**
- [ ] I test di parsing e percentile passano
- [ ] Nessun test pre-esistente è stato rotto


---

## Giorno 6 – Documentare “Performance & SLO” nel README

### Obiettivo del giorno
- Aggiungere una sezione al `README.md` che spieghi come misurare e verificare le performance.


---

### 1. Aggiornare `README.md`

1. Apri `README.md`.
2. Aggiungi una sezione simile (adatta nomi e valori se vuoi):

```markdown
## Performance & SLO

Per valutare la latenza dell'API e verificare gli SLO vengono usati:

- **Middleware di timing** in `src/api/middleware.py`  
  Logga per ogni richiesta una riga del tipo:  
  `HTTP GET /health completed in 5.23 ms` e aggiunge l'header `X-Process-Time-ms`.

- **Statistiche di latenza**  
  ```bash
  python -m src.tools.api_latency_stats
  ```  
  Legge `logs/api/api.log` e calcola, per ogni endpoint, numero di richieste,
  tempo medio e p95 (95° percentile).

- **SLO di latenza**  
  Configurati in `conf/ops/slo.yml` (es. p95 < 600 ms per /predict).  
  Verificabili con:

  ```bash
  python -m src.tools.check_slo
  ```

- **Mini load test**  
  ```bash
  python -m src.tools.load_test_api --n 50
  ```  
  Manda N richieste a `/health` (o altro endpoint) e mostra i tempi lato client,
  generando anche righe di log utili per l'analisi.

Le informazioni di log si trovano in `logs/api/api.log`; i risultati degli
script possono essere usati per avvicinarsi agli SLO definiti
(es. p95 < 600 ms, uptime 99.5%, ecc.).
```

3. Salva il `README.md`.

**Checklist**
- [ ] Il README contiene una sezione chiara su Performance & SLO
- [ ] Sono citati gli script `api_latency_stats`, `check_slo`, `load_test_api`


---

### 2. Giro finale e commit Fase 21

1. Genera un po’ di log con `load_test_api`:

```bash
python -m src.tools.load_test_api --n 30
```

2. Verifica le statistiche e gli SLO:

```bash
python -m src.tools.api_latency_stats
python -m src.tools.check_slo
```

3. Esegui i test:

```bash
pytest
```

4. Se tutto è ok, crea il commit:

```bash
git add conf/ops/slo.yml src/api/middleware.py src/tools/api_latency_stats.py src/tools/load_test_api.py src/tools/check_slo.py tests/test_api_latency_stats.py README.md
git commit -m "Fase 21: baseline performance, SLO e strumenti di verifica"
git push
```

**Checklist (fine Giorno 6 – fine Fase 21)**
- [ ] Middleware di timing attivo e log con latenze
- [ ] Script per statistiche e load test funzionanti
- [ ] SLO configurati e verificabili con `check_slo`
- [ ] README aggiornato e commit creato per chiudere la Fase 21


---

Con la Fase 21 hai aggiunto un tassello importante di **osservabilità delle performance**:

- puoi misurare in modo concreto se l’API sta rispettando i target di latenza,
- puoi vedere come cambiano i tempi in seguito a modifiche o carichi diversi,
- hai un flusso chiaro per analizzare e verificare gli SLO di base.