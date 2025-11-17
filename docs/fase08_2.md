# Fase 08 – Metriche & validazione modello rischio (Parte 2, Giorni 4–6, Windows)

> **Scopo Parte 2**  
> Portare nel codice di produzione quello che hai imparato nel notebook di valutazione:
>
> - esporre una **soglia di rischio predefinita** in un modulo dedicato,
> - aggiornare CLI, API e UI per usare/mostrare questa soglia,
> - aggiungere test di coerenza e chiudere la Fase 08 con un commit.

> **Prerequisito**: hai completato la Parte 1 (`fase08_1.md`) e nel notebook `evaluate_risk_model.ipynb` hai scelto un valore `best_threshold` (es. 0.4 o 0.5).  
> In questa Parte 2 userai quel valore, adattandolo al tuo caso reale.

---

## Struttura Fase 08 – Parte 2

- **Giorno 4** – Creare un modulo `src\ml\risk_threshold.py` con la soglia di default
- **Giorno 5** – Aggiornare CLI, API e UI per usare la soglia
- **Giorno 6** – Test di coerenza, README e commit Git

---

## Giorno 4 – Modulo `risk_threshold.py` con soglia predefinita

### Obiettivo del giorno
Centralizzare in **un solo punto** la soglia di rischio decisa nel notebook, in modo che:

- CLI,
- API,
- UI

la usino tutte in modo coerente.

---

### 1. Creare `src\ml\risk_threshold.py`

1. Apri **VS Code**.
2. Nella barra laterale, espandi `src` → `ml`.
3. Crea un nuovo file chiamato `risk_threshold.py`.
4. Inserisci un contenuto simile al seguente **personalizzando il valore di soglia**:

> **IMPORTANTE**: sostituisci `0.5` con il valore che hai scelto nel notebook (`best_threshold`).

```python
"""Utility per la soglia di rischio predefinita.

Questo modulo centralizza la definizione di una soglia "default" per decidere
se un convoglio è considerato "ad alto rischio" oppure no.
"""

# Soglia di rischio predefinita.
# SOSTITUISCI 0.5 con il valore scelto nel notebook (es. 0.4, 0.6, ecc.).
RISK_THRESHOLD_DEFAULT: float = 0.5


def is_high_risk(prob: float, threshold: float | None = None) -> bool:
    """Ritorna True se la probabilità `prob` è >= soglia.

    Se threshold è None, usa RISK_THRESHOLD_DEFAULT.
    """
    if threshold is None:
        threshold = RISK_THRESHOLD_DEFAULT
    return prob >= threshold
```

5. Salva il file.

**Checklist**
- [ ] Esiste `src\ml\risk_threshold.py`
- [ ] Ho impostato `RISK_THRESHOLD_DEFAULT` al valore scelto nel notebook
- [ ] La funzione `is_high_risk` è definita

---

### 2. Verifica veloce da REPL

Nel terminale (con `.venv` attivo), lancia:

```bash
python
```

e prova:

```python
from src.ml.risk_threshold import RISK_THRESHOLD_DEFAULT, is_high_risk

RISK_THRESHOLD_DEFAULT
is_high_risk(0.2), is_high_risk(0.8)
```

Verifica che i valori tornino come ti aspetti (a seconda della soglia scelta).

**Checklist (fine Giorno 4)**
- [ ] Posso importare `RISK_THRESHOLD_DEFAULT` e `is_high_risk` senza errori
- [ ] Il comportamento di `is_high_risk` è coerente con la soglia scelta

---

## Giorno 5 – Aggiornare CLI, API e UI per usare la soglia

### Obiettivo del giorno
Fare in modo che:

- la **CLI** stampi anche quali convogli superano la soglia,
- la **API** restituisca, oltre a `risk_proba`, anche un campo booleano `is_high_risk`,
- la **UI web** usi `RISK_THRESHOLD_DEFAULT` al posto di una soglia “hardcoded” (0.5).

---

### 1. Aggiornare la CLI `src\ml\predict_cli.py`

Apri `src\ml\predict_cli.py` e:

1. Aggiungi l’import per la soglia, in cima al file:

```python
from src.ml.risk_threshold import RISK_THRESHOLD_DEFAULT, is_high_risk
```

2. Dentro la funzione `main()`, dopo aver ottenuto `df_result`, aggiungi la colonna `is_high_risk`:

Trova il punto in cui hai:

```python
    df_result = predict_convoy_risk_proba(...)
```

e aggiungi subito dopo:

```python
    # Aggiungiamo una colonna che indica se il convoglio supera la soglia di rischio di default
    df_result["is_high_risk"] = df_result["risk_proba"].apply(
        lambda p: is_high_risk(float(p))
    )
```

3. Quando stampi i risultati, aggiorna l’intestazione e le righe, per includere una colonna di alto rischio.

Sostituisci la parte:

```python
    print()
    print("=== Risultati ===")
    print("Convoglio  Prob_rischio")
    for _, row in df_result.iterrows():
        convoy_id = int(row["convoy_id"])
        prob = float(row["risk_proba"])
        print(f"{convoy_id:8d}  {prob:11.3f}")
```

con:

```python
    print()
    print("=== Risultati ===")
    print(f"Soglia di rischio predefinita: {RISK_THRESHOLD_DEFAULT:.2f}")
    print()
    print("Convoglio  Prob_rischio  Alto_rischio")
    for _, row in df_result.iterrows():
        convoy_id = int(row["convoy_id"])
        prob = float(row["risk_proba"])
        high = bool(row["is_high_risk"])
        flag = "SI" if high else "no"
        print(f"{convoy_id:8d}  {prob:11.3f}  {flag:11s}")
```

Salva il file.

**Checklist**
- [ ] La CLI importa `RISK_THRESHOLD_DEFAULT` e `is_high_risk`
- [ ] La CLI aggiunge una colonna `is_high_risk` a `df_result`
- [ ] L’output CLI mostra per ogni convoglio se è “Alto_rischio”

---

### 2. Aggiornare l’API `src\api\app.py`

Apri `src\api\app.py` e:

1. Aggiungi l’import:

```python
from src.ml.risk_threshold import RISK_THRESHOLD_DEFAULT, is_high_risk
```

2. Aggiorna il modello `ConvoyRisk` per includere il campo `is_high_risk`:

Da:

```python
class ConvoyRisk(BaseModel):
    convoy_id: int
    risk_proba: float
```

a:

```python
class ConvoyRisk(BaseModel):
    convoy_id: int
    risk_proba: float
    is_high_risk: bool
```

3. Aggiorna il modello `PredictResponse` per includere la soglia usata:

Da:

```python
class PredictResponse(BaseModel):
    total_minutes: int
    timestep_minutes: int
    n_convoys: int
    results: list[ConvoyRisk]
```

a:

```python
class PredictResponse(BaseModel):
    total_minutes: int
    timestep_minutes: int
    n_convoys: int
    risk_threshold_used: float
    results: list[ConvoyRisk]
```

4. Dentro la funzione `predict_risk`, quando crei `results`, aggiungi `is_high_risk`:

Da:

```python
    results = [
        ConvoyRisk(convoy_id=int(row["convoy_id"]), risk_proba=float(row["risk_proba"]))
        for _, row in df_result.iterrows()
    ]
```

a:

```python
    results = []
    for _, row in df_result.iterrows():
        prob = float(row["risk_proba"])
        results.append(
            ConvoyRisk(
                convoy_id=int(row["convoy_id"]),
                risk_proba=prob,
                is_high_risk=is_high_risk(prob),
            )
        )
```

5. Quando crei `PredictResponse`, aggiungi il campo `risk_threshold_used`:

Da:

```python
    response = PredictResponse(
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        results=results,
    )
```

a:

```python
    response = PredictResponse(
        total_minutes=request.total_minutes,
        timestep_minutes=request.timestep_minutes,
        n_convoys=request.n_convoys,
        risk_threshold_used=RISK_THRESHOLD_DEFAULT,
        results=results,
    )
```

Salva il file.

**Checklist**
- [ ] L’API ora restituisce `risk_threshold_used` nella risposta
- [ ] Ogni elemento in `results` ha `convoy_id`, `risk_proba`, `is_high_risk`

---

### 3. Aggiornare la UI `src\ui\dashboard.py`

Apri `src\ui\dashboard.py` e:

1. Aggiungi l’import in cima al file:

```python
from src.ml.risk_threshold import RISK_THRESHOLD_DEFAULT, is_high_risk
```

2. Dentro il blocco `if run_button:`, dopo aver ottenuto `df_result`, aggiungi la colonna `is_high_risk` **usando la soglia di default**:

Da:

```python
        df_result = predict_convoy_risk_proba(...)
```

a qualcosa di questo tipo:

```python
        df_result = predict_convoy_risk_proba(...)

        # Aggiungiamo la colonna "is_high_risk" usando la soglia di default
        df_result["is_high_risk"] = df_result["risk_proba"].apply(
            lambda p: is_high_risk(float(p))
        )
```

3. Quando ordini e visualizzi la tabella, includi anche la colonna `is_high_risk`:

Ad esempio, puoi mettere:

```python
        df_result_sorted = (
            df_result.sort_values("risk_proba", ascending=False)
            .reset_index(drop=True)
        )

        st.subheader("Risultati – Probabilità di rischio per convoglio (ordinate)")
        st.write(f"Soglia di rischio predefinita: **{RISK_THRESHOLD_DEFAULT:.2f}**")
        st.dataframe(df_result_sorted)
```

4. Quando costruisci la sezione “Convogli ad alto rischio”, usa `df_result_sorted["is_high_risk"]` invece di una soglia hardcoded.

Sostituisci il blocco dove filtravi con `risk_proba >= 0.5` con qualcosa del tipo:

```python
        st.subheader("Convogli ad alto rischio")

        high_risk = df_result_sorted[df_result_sorted["is_high_risk"]]

        if high_risk.empty:
            st.info(
                f"Nessun convoglio supera la soglia di rischio selezionata ({RISK_THRESHOLD_DEFAULT:.2f})."
            )
        else:
            st.warning(
                f"Attenzione: alcuni convogli superano la soglia di rischio ({RISK_THRESHOLD_DEFAULT:.2f}). "
                "Elenco convogli ad alto rischio:"
            )
            st.table(high_risk)
```

5. Il grafico a barre può rimanere lo stesso (usa `risk_proba`), ma ora l’interpretazione è più chiara grazie alla soglia visualizzata.

Salva il file.

**Checklist (fine Giorno 5)**
- [ ] La CLI mostra la soglia usata e indica “Alto_rischio” sì/no
- [ ] L’API restituisce `risk_threshold_used` e `is_high_risk` nel JSON
- [ ] La UI mostra la soglia, colonna `is_high_risk` e convogli filtrati usando `is_high_risk`

---

## Giorno 6 – Test di coerenza, README e commit Git

### Obiettivo del giorno
- Aggiungere almeno un test per `risk_threshold.py`,
- Aggiornare i test API se necessario,
- Aggiornare il `README.md` con la soglia predefinita,
- Fare il commit Git di fine Fase 08.

---

### 1. Test per `risk_threshold.py`

1. In VS Code, nella cartella `tests`, crea (o aggiorna) il file `test_risk_threshold.py`.
2. Inserisci un contenuto simile:

```python
from src.ml.risk_threshold import RISK_THRESHOLD_DEFAULT, is_high_risk


def test_is_high_risk_respects_threshold():
    thr = RISK_THRESHOLD_DEFAULT

    # Valore chiaramente sotto soglia
    assert is_high_risk(thr - 0.1) is False

    # Valore uguale alla soglia
    assert is_high_risk(thr) is True

    # Valore sopra la soglia
    assert is_high_risk(thr + 0.1) is True
```

3. Salva il file.

**Checklist**
- [ ] Esiste `tests\test_risk_threshold.py`
- [ ] Il test verifica il comportamento di `is_high_risk` rispetto a `RISK_THRESHOLD_DEFAULT`

---

### 2. Aggiornare (se serve) i test dell’API

Dal momento che hai cambiato la struttura della risposta di `/predict_risk`, potresti dover aggiornare il test `test_predict_risk_basic` in `tests\test_api_basic.py`.

- Aggiungi controlli per i campi `risk_threshold_used` e `is_high_risk`.

Esempio (solo la parte di asserzioni finali, da adattare al tuo file):

```python
    data = response.json()

    assert "risk_threshold_used" in data
    results = data["results"]
    assert len(results) == 3

    for item in results:
        assert "convoy_id" in item
        assert "risk_proba" in item
        assert "is_high_risk" in item
```

Salva il file dei test.

**Checklist**
- [ ] Il test API è aggiornato per tener conto di `risk_threshold_used` e `is_high_risk`

---

### 3. Eseguire tutti i test con `pytest`

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest
```

Assicurati che:

- tutti i test passino (vecchi + nuovi),
- non ci siano errori su API, CLI, model, dataset, ecc.

**Checklist**
- [ ] `pytest` gira senza errori

---

### 4. Aggiornare README con la soglia di default

Apri `README.md` e aggiungi una sezione (o una nota) in quella dell’API/UI, ad esempio:

```markdown
### Soglia di rischio predefinita

Il sistema utilizza una **soglia di rischio predefinita**:

- `RISK_THRESHOLD_DEFAULT` (definita in `src/ml/risk_threshold.py`)

Questa soglia è stata scelta analizzando precision, recall e F1 nel notebook
`notebooks/evaluate_risk_model.ipynb`. Tutti i componenti (CLI, API, UI)
usano questa soglia per decidere se un convoglio è considerato "ad alto rischio".
```

Salva il `README.md`.

**Checklist**
- [ ] Il README documenta l’esistenza e il ruolo di `RISK_THRESHOLD_DEFAULT`

---

### 5. Commit Git di fine Fase 08

Nel terminale, dalla cartella del progetto:

```bash
git status
```

Dovresti vedere i file nuovi/modificati:

- `src/ml/risk_threshold.py`
- `src/ml/predict_cli.py` (modificato)
- `src/api/app.py` (modificato)
- `src/ui/dashboard.py` (modificato)
- `tests/test_risk_threshold.py`
- `tests/test_api_basic.py` (modificato)
- `README.md`

1. Aggiungi i file:

```bash
git add .
```

2. Crea il commit:

```bash
git commit -m "Fase 08: metriche, soglia rischio e integrazione in CLI/API/UI"
```

3. Verifica che il working tree sia pulito:

```bash
git status
```

Dovresti vedere: `nothing to commit, working tree clean`.

**Checklist (fine Giorno 6 – fine Fase 08)**
- [ ] Ho un notebook di valutazione del modello (`evaluate_risk_model.ipynb`)
- [ ] Ho scelto e documentato una soglia di rischio predefinita
- [ ] Esiste `src/ml/risk_threshold.py` con `RISK_THRESHOLD_DEFAULT` e `is_high_risk`
- [ ] CLI, API e UI usano quella soglia in modo coerente
- [ ] I test (`pytest`) passano
- [ ] Ho creato un commit Git per la Fase 08

---

## Fine Fase 08 – Cosa hai ottenuto

Ora il tuo sistema di rischio convoglio non è più “una scatola nera”:

- hai un **notebook di valutazione** per vedere come si comporta il modello,
- hai scelto una **soglia di rischio** basandoti su metriche chiare,
- la soglia è centralizzata in un modulo Python e usata da CLI, API e UI,
- hai test automatici che controllano il comportamento di `is_high_risk` e dell’API.

Nelle fasi successive potrai:

- migliorare il modello (feature engineering, modelli diversi dalla Logistic Regression),
- arricchire la UI con pagine separate per simulazione, KPI, rischio,
- oppure lavorare su aspetti più “ingegneristici”: configurazione, logging avanzato, riproducibilità e DevOps.
