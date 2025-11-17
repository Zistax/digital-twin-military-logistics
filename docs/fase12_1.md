# Fase 12 – Etica & Privacy + Terminologia (Parte 1, Giorni 1–3, Windows)

> **Scopo Fase 12 (visione generale)**  
> Rendere espliciti nel progetto alcuni principi di **etica, privacy e terminologia** descritti nel documento di architettura:
>
> - niente **PII** nei log (solo ID pseudonimizzati),
> - chiarezza su **GDPR / data minimization**,
> - primi mattoni per una **terminologia configurabile per tenant** (multi-tenant).

In **Parte 1** lavori su:
- documentazione (README + docs separati),
- piccoli controlli tecnici per evitare PII nei dati,
- base per una terminologia configurabile.

In **Parte 2** (file `fase12_2.md`) lavorerai su governance del modello & licensing.

> **Prerequisiti:**
> - Fino alla Fase 11 completata,
> - i test (`pytest`) girano,
> - hai la struttura di logging e dataset già funzionante (Fase 03–04).


---

## Struttura Fase 12 – Parte 1

- **Giorno 1** – Documentazione Etica & Privacy (README + docs/)
- **Giorno 2** – Controlli minimi “no PII nei log/dataset”
- **Giorno 3** – Terminologia configurabile (base) per eventi/label


---

## Giorno 1 – Documentazione Etica & Privacy

### Obiettivo del giorno
- Aggiungere una sezione **Etica & Privacy** nel README,
- creare un documento dedicato in `docs/` che riassuma le decisioni prese,
- chiarire che il progetto lavora solo con dati sintetici / non PII.


---

### 1. Creare cartella `docs` (se non esiste)

1. In **VS Code**, guarda la root del progetto.
2. Se non vedi una cartella `docs`, creala:
   - clic destro nella root → **New Folder** → `docs`

Oppure da terminale (opzionale):

```bash
mkdir docs
```

**Checklist**
- [ ] Esiste la cartella `docs` nella root del progetto


---

### 2. Creare `docs\etica_terminologia_licensing.md`

1. In VS Code, nella cartella `docs`, crea il file:
   - `etica_terminologia_licensing.md`
2. Inserisci una prima struttura (scheletro), ad esempio:

```markdown
# Etica, Privacy, Terminologia & Licensing

## 1. Privacy & GDPR (principi di base)

- Nessun dato personale reale (PII) viene utilizzato.
- I dataset e i log sono **sintetici** e contengono solo ID pseudonimizzati
  (es. `session_id`, `convoy_id`, `vehicle_id` senza riferimenti a persone reali).
- I timestamp sono in UTC e non permettono di risalire a identità reali.

## 2. Data Minimization

- Vengono registrati solo i campi necessari per:
  - analisi operativa,
  - calcolo KPI,
  - training del modello di rischio.
- Campi non necessari vengono omessi.

## 3. Terminologia multi-tenant (overview)

- Alcuni termini di dominio possono essere mappati in modo diverso per tenant/marchio.
- Esempio (solo concettuale):
  - `attack` → `threat_event`
  - `breakdown` → `mech_failure`

## 4. Governance del modello

- Ogni modello addestrato viene salvato con un report JSON che include:
  - parametri di training,
  - metriche principali,
  - eventuale versione/sigla modello.
- Le chiamate API possono essere loggate (in modo aggregato) per audit futuro.

## 5. Licensing

- Il core del progetto e' pensato per una licenza OSI (es. Apache-2.0).
- Plugin, connettori o componenti specifici possono avere licenze diverse.
```

3. Salva il file.

> Nei prossimi passi della Fase 12 e Fase 13 potrai arricchire questo documento con dettagli più precisi.

**Checklist**
- [ ] Esiste `docs\etica_terminologia_licensing.md` con le sezioni 1–5


---

### 3. Aggiungere sezione “Etica & Privacy” al `README.md`

1. Apri `README.md` nella root del progetto.
2. Aggiungi una sezione simile (verso il fondo del file), per esempio:

```markdown
## Etica & Privacy (senza PII)

Questo progetto e' pensato per lavorare con **dati sintetici** e/o dati
che non contengono **informazioni personali identificabili (PII)**.

Principi chiave:

- i log e i dataset usano ID pseudonimizzati (es. `session_id`, `convoy_id`),
- non vengono registrati nomi, cognomi, email, numeri di telefono, targhe reali, ecc.,
- i file di log seguono uno schema documentato (vedi `04 — Logging & Schema Dati`)
  e sono pensati per scopi di simulazione e analisi tecnica.

Per maggiori dettagli, vedi: `docs/etica_terminologia_licensing.md`.
```

3. Salva il README.

**Checklist (fine Giorno 1)**
- [ ] Esiste `docs\etica_terminologia_licensing.md`
- [ ] `README.md` ha una sezione “Etica & Privacy” che rimanda a `docs/`


---

## Giorno 2 – Controlli minimi “no PII” in schema/dataset

### Obiettivo del giorno
- Aggiungere un **piccolo test automatico** che controlli che i dataset/log non abbiano colonne chiaramente PII,
- documentare in un punto unico quali colonne **sono ammesse** (whitelist leggera).


---

### 1. Definire una lista di nomi colonna vietati (ban-list)

1. Crea (o apri) il file `tests\test_schema_no_pii.py`.
2. Inserisci qualcosa come:

```python
from pathlib import Path

import pandas as pd


# Nomi colonna vietati (chiaramente PII)
PII_BANNED_COLUMNS = {
    "name",
    "first_name",
    "last_name",
    "email",
    "phone",
    "plate",
    "license_plate",
    "cf",
    "codice_fiscale",
}


def test_convoy_risk_dataset_has_no_pii_columns():
    """Il dataset principale di rischio non deve contenere colonne chiaramente PII."""
    dataset_path = Path("data/processed/convoy_risk_dataset.csv")
    if not dataset_path.exists():
        # Se il dataset non esiste, saltiamo il test (oppure falliamo, in base a come preferisci).
        return

    df = pd.read_csv(dataset_path)
    cols = {c.lower() for c in df.columns}

    assert PII_BANNED_COLUMNS.isdisjoint(
        cols
    ), f"Trovate colonne potenzialmente PII nel dataset di rischio: {PII_BANNED_COLUMNS & cols}"
```

3. Salva il file.

> Questo test è molto semplice: controlla che nessuna colonna abbia un nome “sospetto”.  
> Non garantisce al 100% l’assenza di PII, ma ti dà una **rete di sicurezza base**.

**Checklist**
- [ ] Esiste `tests\test_schema_no_pii.py` con una ban-list di nomi colonna vietati


---

### 2. (Opzionale) Estendere il test anche ai log eventi

Se i tuoi log eventi vengono già salvati in `data/raw/session_..._events.csv`, puoi aggiungere un altro test simile.

Nel file `tests\test_schema_no_pii.py`, aggiungi:

```python
def test_events_logs_have_no_pii_columns():
    """I file di log eventi non devono avere colonne chiaramente PII."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        return

    # Cerchiamo file che finiscono con _events.csv
    for csv_path in raw_dir.glob("*_events.csv"):
        df = pd.read_csv(csv_path)
        cols = {c.lower() for c in df.columns}

        assert PII_BANNED_COLUMNS.isdisjoint(
            cols
        ), f"File {csv_path} contiene colonne potenzialmente PII: {PII_BANNED_COLUMNS & cols}"
```

Salva il file.

**Checklist**
- [ ] Il test controlla anche eventuali file `*_events.csv` in `data/raw`


---

### 3. Lanciare `pytest` (o `run_quality.bat`) per verificare i test

1. Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pytest tests/test_schema_no_pii.py
```

oppure:

```bash
run_quality.bat
```

2. Assicurati che:
   - il test passi,
   - oppure, se fallisce, l’errore indichi nomi colonna sospetti che puoi rinominare.

> Se hai colonne “di test” che si chiamano “email_demo” o simili, valuta se rinominarle.

**Checklist (fine Giorno 2)**
- [ ] I nuovi test “no PII” passano
- [ ] Se necessario, ho rinominato eventuali colonne sospette nei dataset/log


---

## Giorno 3 – Terminologia configurabile (base)

### Obiettivo del giorno
- Introdurre una base per la **terminologia multi-tenant**:
  - un file YAML con mapping dei termini,
  - una piccola utility Python per caricarlo,
  - un primo utilizzo nella UI o nell’API (anche solo per una label).


---

### 1. Creare `conf\terminology\default.yml`

1. In VS Code, nella cartella `conf`, crea una sottocartella `terminology`:

   - `conf/terminology`

2. Dentro `conf\terminology`, crea il file `default.yml`.
3. Inserisci un contenuto tipo:

```yaml
terminology:
  # Termini "canonici" → label tenant di default
  attack: "threat_event"
  breakdown: "mech_failure"
  mission_complete: "mission_complete"
  depot: "logistics_node"
```

4. Salva il file.

**Checklist**
- [ ] Esiste `conf\terminology\default.yml` con una sezione `terminology:`


---

### 2. Creare un piccolo loader di terminologia

1. In `src\config`, crea (se non esiste) il file `terminology_loader.py`.
2. Inserisci il seguente codice:

```python
from __future__ import annotations

from pathlib import Path
from typing import Dict

import os
import yaml

BASE_CONF_DIR = Path("conf")


def load_terminology(env: str | None = None) -> Dict[str, str]:
    """Carica il mapping terminologico per l'ambiente indicato.

    - env: nome dell'ambiente (default, dev, prod...). Se None, usa la variabile
      d'ambiente TERMINOLOGY_ENV, altrimenti 'default'.
    """
    if env is None:
        env = os.environ.get("TERMINOLOGY_ENV", "default")

    path = BASE_CONF_DIR / "terminology" / f"{env}.yml"
    if not path.exists():
        raise FileNotFoundError(f"File terminologia non trovato: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    term_map = data.get("terminology", {})
    if not isinstance(term_map, dict):
        raise ValueError(f"Sezione 'terminology' non valida in {path}")

    # Convertiamo le chiavi in stringhe lower-case, per sicurezza
    normalized = {str(k).lower(): str(v) for k, v in term_map.items()}
    return normalized


def translate_term(term: str, mapping: Dict[str, str]) -> str:
    """Traduce un termine canonico usando il mapping; se non trovato, restituisce l'originale."""
    return mapping.get(term.lower(), term)
```

3. Salva il file.

**Checklist**
- [ ] Esiste `src\config\terminology_loader.py` con `load_terminology` e `translate_term`


---

### 3. Usare la terminologia almeno in un punto (UI o API)

Come primo uso realistico, puoi far apparire questi label nella **UI Streamlit**, ad esempio in un testo descrittivo.

1. Apri `src\ui\dashboard.py`.
2. In cima, aggiungi l’import:

```python
from src.config.terminology_loader import load_terminology, translate_term
```

3. Dentro `main()`, all’inizio, carica il mapping:

```python
    term_map = {}
    try:
        term_map = load_terminology()
    except FileNotFoundError:
        # Terminologia non configurata; useremo i termini canonici
        term_map = {}
```

4. Quando descrivi il tipo di rischio (ad esempio nel testo iniziale della pagina), puoi usare:

```python
    attack_label = translate_term("attack", term_map)
    breakdown_label = translate_term("breakdown", term_map)

    st.write(
        f"""
        Il modello stima il rischio per i convogli considerando diversi tipi di eventi
        (es. `{attack_label}`, `{breakdown_label}`, ecc.), in base al dataset di addestramento.
        """
    )
```

5. Salva il file.

> In futuro, potrai usare questa terminologia anche in grafici, legende, tooltip, nomi colonne, ecc.

**Checklist**
- [ ] La UI carica (senza crash) il mapping da `conf/terminology/default.yml`
- [ ] Il testo iniziale della UI utilizza `translate_term` per mostrare i label


---

### 4. Verifica finale della Parte 1

1. Lancia `run_quality.bat` oppure almeno:

```bash
pytest
```

2. Avvia l’API (se vuoi controllare che tutto sia ancora ok) e la UI:

```bash
uvicorn src.api.app:app --reload
streamlit run src/ui/dashboard.py
```

3. Controlla che:
   - la UI si apra,
   - compaia il testo con i termini tradotti (`threat_event`, `mech_failure`),
   - i test “no PII” passino.

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] Documentazione etica & privacy creata (`docs/etica_terminologia_licensing.md`)
- [ ] Sezione “Etica & Privacy” presente in `README.md`
- [ ] Test automatici “no PII” per dataset e log base
- [ ] YAML di terminologia + loader + primo uso in UI

---

Con questa Parte 1 hai reso **espliciti** nel progetto alcuni principi etici e di privacy
e hai introdotto il primo tassello di **terminologia configurabile**.
Nella Parte 2 (`fase12_2.md`) lavorerai su:

- governance del modello (versioni, log di decisioni),
- struttura di licensing (Apache-2.0 per il core + nota per plugin/proprietario).
