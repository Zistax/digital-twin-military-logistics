# Fase 21 – Performance baseline & SLO (Parte 1, Giorni 1–3, Windows)

> **Obiettivo pratico (Parte 1)**  
> Strumentare l’API per avere una **baseline di performance** e iniziare a misurare
> se sei vicino agli SLO (es. p95 < 600 ms):
>
> - aggiungere un **middleware di timing** sull’API,
> - loggare il tempo di risposta per ogni richiesta,
> - creare uno script che legge i log e calcola **media / p95** per endpoint,
> - opzionale: piccolo script di “micro load test” su `/health`.


---

## Struttura Fase 21 – Parte 1

- **Giorno 1** – Middleware FastAPI per misurare e loggare le latenze
- **Giorno 2** – Script `api_latency_stats.py` per calcolare media e p95
- **Giorno 3** – Mini load test su `/health` (`load_test_api.py`) per generare dati


---

## Giorno 1 – Middleware di timing per l’API

### Obiettivo del giorno
- Aggiungere un **middleware** che misura il tempo di ogni richiesta e scrive una riga di log,
- esporre anche un header `X-Process-Time-ms` nella risposta per debugging.


---

### 1. Creare `src\api\middleware.py`

1. In **VS Code**, nella cartella `src\api`, crea il file:

   - `middleware.py`

2. Inserisci il seguente contenuto:

```python
from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger("api")


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware che misura il tempo di elaborazione di ogni richiesta.

    - Logga una riga del tipo:
      "HTTP GET /predict completed in 123.45 ms"
    - Aggiunge l'header X-Process-Time-ms alla risposta
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0

        method = request.method
        path = request.url.path

        logger.info(
            "HTTP %s %s completed in %.2f ms",
            method,
            path,
            duration_ms,
        )

        # Aggiungiamo un header con il tempo di elaborazione
        response.headers["X-Process-Time-ms"] = f"{duration_ms:.2f}"

        return response
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/api/middleware.py` con `RequestTimingMiddleware` definito


---

### 2. Registrare il middleware in `app.py`

1. Apri `src\api\app.py`.
2. In cima al file, tra gli import, aggiungi:

```python
from src.api.middleware import RequestTimingMiddleware
```

3. Subito dopo la creazione dell’oggetto FastAPI, dove hai qualcosa tipo:

```python
app = FastAPI(...)
logger = setup_api_logger()
```

aggiungi la riga:

```python
app.add_middleware(RequestTimingMiddleware)
```

In modo che la sezione sia simile a:

```python
app = FastAPI(...)

logger = setup_api_logger()
app.add_middleware(RequestTimingMiddleware)
```

4. Salva il file.

**Checklist**
- [ ] `app.py` importa `RequestTimingMiddleware`
- [ ] `app.add_middleware(RequestTimingMiddleware)` viene chiamato dopo la creazione di `app`


---

### 3. Verifica del middleware

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
uvicorn src.api.app:app --reload
```

2. Apri il browser e visita un paio di endpoint:

- `http://127.0.0.1:8000/health`
- magari anche `/predict` o `/simulate` da Swagger.

3. In ogni risposta HTTP, controlla gli header (da browser o usando strumenti come `curl`):  
   dovresti vedere qualcosa come:

```text
X-Process-Time-ms: 12.34
```

4. Apri il file `logs/api/api.log` e verifica che compaiano righe tipo:

```text
2025-11-16 14:10:12,345 [INFO] api - HTTP GET /health completed in 5.23 ms
2025-11-16 14:10:15,678 [INFO] api - HTTP POST /predict completed in 120.87 ms
```

**Checklist (fine Giorno 1)**
- [ ] Ogni chiamata agli endpoint genera una riga di log con latenza
- [ ] Le risposte hanno l’header `X-Process-Time-ms`


---

## Giorno 2 – Script `api_latency_stats.py` (media e p95 per endpoint)

### Obiettivo del giorno
- Creare uno script che legge `logs/api/api.log`,
- estrae da ogni riga `HTTP ... completed in XX.XX ms`,
- aggrega per path (`/health`, `/predict`, `/simulate`, `/optimize`, …),
- calcola **media** e **p95** dei tempi, e stampa un report leggibile.


---

### 1. Creare `src\tools\api_latency_stats.py`

1. In **VS Code**, nella cartella `src\tools` (già creata in Fase 20), crea il file:

   - `api_latency_stats.py`

2. Inserisci il seguente codice:

```python
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import re
import statistics


LOG_PATH_DEFAULT = Path("logs") / "api" / "api.log"

# Esempio di riga di log che vogliamo parsare:
# 2025-11-16 14:10:12,345 [INFO] api - HTTP GET /health completed in 5.23 ms
LATENCY_PATTERN = re.compile(
    r"HTTP\s+(?P<method>\S+)\s+(?P<path>\S+)\s+completed in\s+(?P<ms>[0-9.]+)\s+ms"
)


def parse_latency_line(line: str) -> Tuple[str, float] | None:
    """Parsa una riga di log e ritorna (path, durata_ms) se compatibile, altrimenti None."""
    m = LATENCY_PATTERN.search(line)
    if not m:
        return None

    path = m.group("path")
    try:
        ms = float(m.group("ms"))
    except ValueError:
        return None

    return path, ms


def load_latencies(log_path: Path = LOG_PATH_DEFAULT) -> Dict[str, List[float]]:
    """Legge il file di log e costruisce un dict: path -> lista di latenze (ms)."""
    if not log_path.exists():
        raise FileNotFoundError(f"File di log non trovato: {log_path}")

    latencies: Dict[str, List[float]] = {}

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            parsed = parse_latency_line(line)
            if not parsed:
                continue
            path, ms = parsed
            latencies.setdefault(path, []).append(ms)

    return latencies


def percentile(values: List[float], p: float) -> float:
    """Calcola un percentile semplice (p ∈ [0, 100]) su una lista di valori non vuota."""
    if not values:
        raise ValueError("Lista vuota per percentile")
    if p < 0 or p > 100:
        raise ValueError("p deve essere tra 0 e 100")

    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return float(sorted_vals[int(k)])
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return float(d0 + d1)


def summarize_latencies(latencies: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
    """Ritorna un dict: path -> { 'count', 'mean_ms', 'p95_ms' }"""
    summary: Dict[str, Dict[str, float]] = {}

    for path, vals in latencies.items():
        if not vals:
            continue

        mean_ms = statistics.mean(vals)
        p95_ms = percentile(vals, 95.0)

        summary[path] = {
            "count": float(len(vals)),
            "mean_ms": float(mean_ms),
            "p95_ms": float(p95_ms),
        }

    return summary


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Statistiche di latenza API (media e p95).")
    parser.add_argument(
        "--log-path",
        type=str,
        default=str(LOG_PATH_DEFAULT),
        help="Percorso del file di log API (default: logs/api/api.log)",
    )

    args = parser.parse_args()
    log_path = Path(args.log_path)

    latencies = load_latencies(log_path)
    if not latencies:
        print(f"Nessuna riga di latenza trovata in {log_path}.")
        return

    summary = summarize_latencies(latencies)

    print(f"=== Statistiche di latenza API (file: {log_path}) ===")
    for path, stats in sorted(summary.items(), key=lambda x: x[0]):
        print(
            f"{path:15s} n={int(stats['count']):4d}  "
            f"mean={stats['mean_ms']:.2f} ms  p95={stats['p95_ms']:.2f} ms"
        )


if __name__ == "__main__":
    main()
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src/tools/api_latency_stats.py`
- [ ] La funzione `parse_latency_line` estrae path e ms da una riga di log
- [ ] `summarize_latencies` ritorna media e p95 per ogni path


---

### 2. Prova dello script di statistiche

1. Assicurati di avere già qualche riga nel log (da ieri: chiamate a `/health`, `/predict`, ecc.).
   In caso contrario, genera un po’ di traffico manualmente con il browser o Swagger.

2. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
python -m src.tools.api_latency_stats
```

3. Dovresti vedere un output simile a:

```text
=== Statistiche di latenza API (file: logs/api/api.log) ===
/health         n=  10  mean=  5.23 ms  p95=  7.01 ms
/predict        n=  20  mean=120.45 ms  p95=180.10 ms
/simulate       n=   5  mean=350.10 ms  p95=400.00 ms
```

**Checklist (fine Giorno 2)**
- [ ] `python -m src.tools.api_latency_stats` gira senza errori
- [ ] Vedi almeno una riga di statistiche per `/health` (se hai richieste nel log)


---

## Giorno 3 – Mini load test su `/health` (`load_test_api.py`)

### Obiettivo del giorno
- Creare uno script molto semplice che manda N richieste a `/health`,
- misurare tempo medio e p95 locale,
- generare righe nel log per alimentare `api_latency_stats`.


---

### 1. Creare `src\tools\load_test_api.py`

1. In **VS Code**, nella cartella `src\tools`, crea il file:

   - `load_test_api.py`

2. Inserisci il seguente codice:

```python
from __future__ import annotations

import time
from pathlib import Path
from typing import List

import requests

from .api_latency_stats import percentile


DEFAULT_URL = "http://127.0.0.1:8000/health"


def run_load_test(
    url: str = DEFAULT_URL,
    n_requests: int = 50,
) -> None:
    """Manda n_requests GET all'endpoint specificato e stampa qualche statistica locale."""
    durations: List[float] = []

    print(f"Eseguo load test su {url} con {n_requests} richieste...")

    for i in range(n_requests):
        start = time.perf_counter()
        resp = requests.get(url, timeout=5)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        durations.append(elapsed_ms)

        if resp.status_code != 200:
            print(f"[{i+1}] Status code {resp.status_code} (tempo={elapsed_ms:.2f} ms)")
        else:
            print(f"[{i+1}] OK (tempo={elapsed_ms:.2f} ms)")

    if not durations:
        print("Nessuna richiesta eseguita.")
        return

    mean_ms = sum(durations) / len(durations)
    p95_ms = percentile(durations, 95.0)

    print()
    print("=== Risultati load test (client-side) ===")
    print(f"Richieste totali: {len(durations)}")
    print(f"Tempo medio:      {mean_ms:.2f} ms")
    print(f"Tempo p95:        {p95_ms:.2f} ms")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Mini load test su endpoint API (default: /health).")
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_URL,
        help="URL completo dell'endpoint da testare (default: http://127.0.0.1:8000/health)",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=50,
        help="Numero di richieste da inviare (default: 50)",
    )

    args = parser.parse_args()

    run_load_test(url=args.url, n_requests=args.n)


if __name__ == "__main__":
    main()
```

3. Salva il file.

> Nota: questo **non** è un vero strumento di load test professionale, ma è sufficiente
> per generare un po’ di traffico e farsi un’idea dei tempi di risposta.

**Checklist**
- [ ] Esiste `src/tools/load_test_api.py` con `run_load_test` e `main()`


---

### 2. Eseguire il mini load test

1. Avvia l’API (se non è già in esecuzione):

```bash
uvicorn src.api.app:app --reload
```

2. In un altro terminale (con `.venv` attivo), lancia:

```bash
python -m src.tools.load_test_api --n 30
```

3. Dovresti vedere le 30 richieste con i rispettivi tempi e un riepilogo finale.

4. Poi esegui di nuovo:

```bash
python -m src.tools.api_latency_stats
```

per vedere come si sono aggiornate le statistiche nel log.

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] `load_test_api` funziona e genera richieste senza errori
- [ ] `api_latency_stats` mostra statistiche aggiornate per `/health`
- [ ] Hai una prima idea di media e p95 dei tempi del tuo sistema


---

Con la Parte 1 della Fase 21 hai:

- uno **strumento di timing** integrato nell’API,
- log strutturati con tempi per endpoint,
- uno script per calcolare media e p95,
- un mini load test per generare traffico e misure.

Nella **Parte 2** userai queste informazioni per collegarle a degli SLO base
(magari in un file YAML) e avere uno script che ti dice se sei “entro SLO” oppure no.