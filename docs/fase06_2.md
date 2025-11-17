# Fase 06 – API REST per il rischio convoglio (Parte 2, Giorni 4–6, Windows)

> **Scopo Parte 2**  
> Aggiungere **test automatici** per l'API FastAPI, integrare l'API nel flusso di controlli e chiudere la Fase 06 con un commit Git pulito.

In questa Parte 2 farai:

- **Giorno 4** – Creare test per l'API usando il `TestClient` di FastAPI
- **Giorno 5** – (Opzionale ma consigliato) Aggiornare `run_checks.bat` per includere test e note sull'API
- **Giorno 6** – Esecuzione completa (test + API) e commit Git di fine Fase 06

> Assicurati di aver completato la **Parte 1** (`fase06_1.md`) e che l'API risponda correttamente.

---

## Giorno 4 – Test automatici per l'API FastAPI

### Obiettivo del giorno
Creare test che verificano:

- che l'endpoint `/health` risponda `{"status": "ok"}`,
- che l'endpoint `/predict_risk` funzioni con parametri validi,
- che venga gestito lo scenario in cui il modello non esiste (se vuoi testarlo).

Userai il `TestClient` fornito da FastAPI (basato su `requests`).

---

### 1. Creare `tests\test_api_basic.py`

1. Apri **VS Code**.
2. Nella cartella `tests`, crea il file `test_api_basic.py`.
3. Inserisci il seguente contenuto:

```python
from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


def test_predict_risk_basic(monkeypatch):
    """Test di base per /predict_risk con valori standard.

    Usiamo monkeypatch per evitare di caricare il vero modello da disco,
    sostituendo load_risk_model con una versione fittizia se necessario.
    """
    from src.api.app import load_risk_model, predict_convoy_risk_proba

    class DummyModel:
        def predict_proba(self, X):
            # Prob classe 0 = 0.8, classe 1 = 0.2
            import numpy as np

            n_samples = len(X)
            return np.tile([0.8, 0.2], (n_samples, 1))

    def dummy_load_risk_model(path):
        return DummyModel()

    def dummy_predict_convoy_risk_proba(model, total_minutes, timestep_minutes, n_convoys):
        import pandas as pd

        return pd.DataFrame(
            {
                "convoy_id": list(range(1, n_convoys + 1)),
                "risk_proba": [0.2] * n_convoys,
            }
        )

    # Sostituiamo temporaneamente le funzioni reali con le versioni dummy
    monkeypatch.setattr("src.api.app.load_risk_model", dummy_load_risk_model)
    monkeypatch.setattr("src.api.app.predict_convoy_risk_proba", dummy_predict_convoy_risk_proba)

    payload = {
        "total_minutes": 120,
        "timestep_minutes": 10,
        "n_convoys": 3,
    }

    response = client.post("/predict_risk", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_minutes"] == 120
    assert data["timestep_minutes"] == 10
    assert data["n_convoys"] == 3

    results = data["results"]
    assert len(results) == 3
    for item in results:
        assert "convoy_id" in item
        assert "risk_proba" in item
```

4. Salva il file.

> **Nota**: usiamo `monkeypatch` (fixture di pytest) per evitare di dover caricare davvero il modello da disco durante il test.  
> In questo modo il test è:
> - più veloce,
> - più robusto (non dipende da file esterni).

**Checklist**
- [ ] Esiste `tests\test_api_basic.py`
- [ ] Sono presenti i test `test_health_ok` e `test_predict_risk_basic`

---

### 2. Eseguire i test con `pytest`

Nel terminale (con `.venv` attivo), dalla cartella del progetto:

```bash
pytest
```

Controlla che:

- passino tutti i test esistenti (Fase 01–05),
- passino anche i nuovi test `test_api_basic.py`.

Se vedi errori relativi a import di `fastapi.testclient`, verifica che `fastapi` sia installato correttamente (`pip show fastapi`) e che il virtualenv sia attivo.

**Checklist (fine Giorno 4)**
- [ ] `pytest` gira senza errori
- [ ] I test API in `test_api_basic.py` passano

---

## Giorno 5 – Aggiornare (opzionale) `run_checks.bat` e note sull'API

### Obiettivo del giorno
- (Opzionale) Aggiornare `run_checks.bat` per ricordarti di eseguire i test e (se vuoi) avviare l'API,
- Aggiungere qualche riga nel `README.md` per documentare l'esistenza dell'API REST.

---

### 1. Aggiornare `run_checks.bat` (opzionale ma utile)

Apri il file `run_checks.bat` nella root del progetto.

Puoi aggiungere una sezione che:

- attiva l'ambiente virtuale,
- esegue `pytest`,
- (opzionale) stampa un messaggio su come avviare l'API.

Esempio (puoi adattarlo a quello che hai già):

```bat
@echo off
echo ==============================
echo Attivo l'ambiente virtuale...
echo ==============================

call .venv\Scripts\activate.bat

echo.
echo ==============================
echo Eseguo i test con pytest...
echo ==============================

pytest

echo.
echo ==============================
echo Per avviare l'API REST usa:
echo   uvicorn src.api.app:app --reload
echo ==============================

echo.
echo Controlli completati.
pause
```

Salva il file.

**Checklist (opzionale)**
- [ ] `run_checks.bat` contiene un riferimento su come avviare l'API REST

---

### 2. Aggiornare `README.md` (breve sezione API)

Apri `README.md` nella root del progetto e aggiungi una breve sezione, per esempio:

```markdown
## API REST rischio convoglio

Il progetto espone un'API REST locale (FastAPI) per stimare il rischio dei convogli.

- Avvio server (da root progetto, con ambiente attivo):

  ```bash
  uvicorn src.api.app:app --reload
  ```

- Endpoint principali:
  - `GET /health` → restituisce `{"status": "ok"}`
  - `POST /predict_risk` → accetta JSON con:
    - `total_minutes` (int)
    - `timestep_minutes` (int)
    - `n_convoys` (int)
    e restituisce le probabilità di rischio per ogni convoglio.

- Documentazione interattiva (Swagger UI):
  - `http://127.0.0.1:8000/docs`
```

Salva il `README.md`.

**Checklist (fine Giorno 5)**
- [ ] (Opzionale) `run_checks.bat` aggiornato con info sull'API
- [ ] `README.md` aggiornato con una sezione che descrive l'API REST

---

## Giorno 6 – Verifiche finali e commit Git di fine Fase 06

### Obiettivo del giorno
- Eseguire un giro completo di test,
- Verificare che l'API parta correttamente,
- Creare un commit Git che contrassegni la chiusura della Fase 06.

---

### 1. Giro di test completo

Nel terminale (con `.venv` attivo), dalla cartella del progetto:

```bash
pytest
```

Assicurati che:

- passino i test di simulatore,
- passino i test delle metriche e del modello,
- passino i test di prediction e dell'API.

**Checklist**
- [ ] `pytest` passa per tutti i moduli (sim, metrics, ml, api)

---

### 2. Avviare l'API e fare un test a mano

1. Avvia l'API in un terminale:

```bash
uvicorn src.api.app:app --reload
```

2. Nel browser, verifica:
   - `http://127.0.0.1:8000/health`
   - `http://127.0.0.1:8000/docs`

3. Da `/docs`, prova una chiamata a `POST /predict_risk` con qualche combinazione di parametri.

**Checklist**
- [ ] L'API parte senza errori
- [ ] `/health` e `/docs` sono raggiungibili
- [ ] `POST /predict_risk` risponde correttamente

---

### 3. Commit Git di fine Fase 06

Nel terminale (sempre nella cartella del progetto):

```bash
git status
```

Dovresti vedere i nuovi file (`src/api/app.py`, `tests/test_api_basic.py`, eventuali modifiche a `README.md`, `run_checks.bat`, ecc.).

1. Aggiungi i file:

```bash
git add .
```

2. Crea il commit:

```bash
git commit -m "Fase 06: API REST FastAPI per rischio convoglio"
```

3. Verifica che il working tree sia pulito:

```bash
git status
```

Dovresti vedere: `nothing to commit, working tree clean`.

**Checklist (fine Giorno 6)**

- [ ] Ho eseguito i test (`pytest`) con successo
- [ ] Ho verificato a mano che l'API REST funziona
- [ ] Ho creato il commit Git “Fase 06: API REST FastAPI per rischio convoglio”

---

## Fine Fase 06 – Cosa hai ottenuto

Con la Fase 06 completata, ora hai:

- un **modello di rischio** addestrato (Fase 04–05),
- un **modulo di prediction riutilizzabile** (`src\ml\predict.py`),
- una **CLI locale** (`python -m src.ml.predict_cli`),
- una **API REST FastAPI** con endpoint `/predict_risk`,
- test automatici per il simulatore, le metriche, il modello e l'API.

Questo ti mette in una posizione ottima per le fasi successive, dove potrai:

- costruire una **UI web semplice** (es. con Streamlit o una pagina HTML che chiama l'API),
- arricchire il simulatore e il dataset con più feature,
- migliorare il modello di rischio.

Quando sei pronto, potrai passare alla Fase 07 dedicata alla **UI grafica** o ad altre estensioni che decideremo insieme.
