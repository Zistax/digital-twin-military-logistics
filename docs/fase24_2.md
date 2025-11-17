# Fase 24 – DevOps & Qualità locale (Parte 2, Giorni 4–6, Windows)

> **Obiettivo pratico (Parte 2)**  
> Collegare gli strumenti di qualità in:
>
> - uno **script Windows** (`tasks.bat`) per lanciare tutti i check,
> - una pipeline **CI** (GitHub Actions) base,
> - una sezione `DevOps & Qualità` nel `README.md` che riassume tutto.

Così avrai sia comandi comodi in locale, sia una verifica automatica sui commit/pull request.


---

## Struttura Fase 24 – Parte 2

- **Giorno 4** – Script `tasks.bat` con comandi standard (test/lint/typecheck/quality)
- **Giorno 5** – Pipeline CI base GitHub Actions (`.github/workflows/ci.yml`)
- **Giorno 6** – Sezione `DevOps & Qualità` nel README + giro completo


---

## Giorno 4 – Script `tasks.bat` (helper Windows)

### Obiettivo del giorno
- Creare uno script `.bat` che ti permette di lanciare comandi standard con:
  - `tasks.bat test`
  - `tasks.bat lint`
  - `tasks.bat typecheck`
  - `tasks.bat quality`


---

### 1. Creare `tasks.bat` nella root del progetto

1. Nella root del progetto, crea il file:

   - `tasks.bat`

2. Inserisci questo contenuto:

```bat
@echo off
REM Script helper per comandi di qualità (Windows)

if "%1"=="" goto help

set CMD=%1

call .venv\Scripts\activate

if "%CMD%"=="test" goto test
if "%CMD%"=="lint" goto lint
if "%CMD%"=="format" goto format
if "%CMD%"=="typecheck" goto typecheck
if "%CMD%"=="quality" goto quality

echo Comando non riconosciuto: %CMD%
goto help

:test
echo Eseguo test (pytest)...
pytest
goto end

:lint
echo Eseguo lint (ruff in check mode)...
ruff check .
goto end

:format
echo Eseguo formattazione (black)...
black .
goto end

:typecheck
echo Eseguo controllo tipi (mypy)...
mypy src
goto end

:quality
echo Eseguo quality completa: lint + typecheck + test con coverage...
ruff check . || goto end
mypy src || goto end
pytest --cov=src --cov-report=term-missing
goto end

:help
echo Utilizzo: tasks.bat [comando]
echo.
echo Comandi disponibili:
echo   test       - esegue pytest
echo   lint       - esegue ruff in modalita' check
echo   format     - formatta il codice con black
echo   typecheck  - esegue mypy su src/
echo   quality    - lint + typecheck + pytest con coverage
echo.

:end
```

3. Salva il file.

**Checklist**
- [ ] Esiste `tasks.bat` nella root del progetto


---

### 2. Prova dei comandi principali

1. Dal terminale **cmd** (non PowerShell, per semplicità), nella root del progetto:

```bash
tasks.bat test
tasks.bat lint
tasks.bat typecheck
tasks.bat quality
```

2. Verifica che ogni comando:

- attivi correttamente `.venv\Scripts\activate`,
- esegua il tool previsto,
- in caso di errori (es. lint), li mostri chiaramente.

**Checklist (fine Giorno 4)**
- [ ] `tasks.bat test` funziona
- [ ] `tasks.bat lint` funziona
- [ ] `tasks.bat typecheck` funziona
- [ ] `tasks.bat quality` esegue tutti i check


---

## Giorno 5 – Pipeline CI base (GitHub Actions)

### Obiettivo del giorno
- Aggiungere una pipeline CI base che, ad ogni `push` / `pull_request` su GitHub:
  - installa le dipendenze,
  - esegue lint (ruff), test (pytest+coverage), typecheck (mypy),
  - fallisce se uno di questi step fallisce.


---

### 1. Creare la cartella `.github/workflows`

1. Nella root del progetto, crea le cartelle:

   - `.github`
   - `.github/workflows`

Da terminale:

```bash
mkdir .github
mkdir .github\workflows
```

**Checklist**
- [ ] Esiste `.github/workflows`


---

### 2. Creare il workflow `ci.yml`

1. Dentro `.github/workflows`, crea il file:

   - `ci.yml`

2. Inserisci una pipeline semplice (puoi adattare la versione di Python):

```yaml
name: CI

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Lint (ruff)
        run: |
          ruff check .

      - name: Typecheck (mypy)
        run: |
          mypy src

      - name: Tests with coverage
        run: |
          pytest --cov=src --cov-report=term-missing
```

3. Salva il file.

> Quando farai `git push` su GitHub, vedrai il job **CI** partire nella sezione “Actions”
> del repository.

**Checklist**
- [ ] Esiste `.github/workflows/ci.yml` con lint + test + typecheck


---

### 3. Primo giro di CI

1. Fai un commit con le modifiche di Fase 24:

```bash
git add requirements-dev.txt .pre-commit-config.yaml tasks.bat mypy.ini pytest.ini .github/workflows/ci.yml
git commit -m "Fase 24: setup DevOps locale (pre-commit, CI, tasks.bat)"
git push
```

2. Vai su GitHub → tab “Actions” e controlla che il workflow **CI** parta.

3. Se uno degli step fallisce (lint, mypy, test), guarda il log e correggi i problemi
   in locale usando `tasks.bat quality`, poi ripeti `git push`.

**Checklist (fine Giorno 5)**
- [ ] La pipeline CI gira su GitHub
- [ ] Gli step lint / typecheck / test sono tutti verdi


---

## Giorno 6 – Sezione “DevOps & Qualità” nel README


### Obiettivo del giorno
- Aggiornare il `README.md` per spiegare a te (e ad altri) come usare questi strumenti,
- definire obiettivi base (es. nessun errore ruff/mypy, coverage minima).


---

### 1. Aggiornare il README

1. Apri `README.md`.
2. Aggiungi (o completa) una sezione simile:

```markdown
## DevOps & Qualita'

Per mantenere il progetto in buono stato nel tempo sono stati configurati
alcuni strumenti di qualita' locale e una pipeline CI.

### Strumenti locali

- **Formattazione & linting**
  - `black` per la formattazione automatica
  - `ruff` per linting veloce (import inutilizzati, stile, ecc.)
  - gestiti tramite **pre-commit** (`.pre-commit-config.yaml`)

- **Test & coverage**
  - `pytest` per i test
  - `pytest-cov` per misurare coverage:
    ```bash
    pytest --cov=src --cov-report=term-missing
    ```

- **Controllo tipi**
  - `mypy` con configurazione in `mypy.ini`:
    ```bash
    mypy src
    ```

- **Script helper (Windows)**
  - `tasks.bat test` – esegue pytest
  - `tasks.bat lint` – esegue ruff
  - `tasks.bat typecheck` – esegue mypy
  - `tasks.bat quality` – lint + mypy + pytest con coverage

### Integrazione CI (GitHub Actions)

Ogni `push` / `pull_request` su `main`/`master` esegue automaticamente:

```bash
ruff check .
mypy src
pytest --cov=src --cov-report=term-missing
```

Il workflow e' definito in:

- `.github/workflows/ci.yml`

**Obiettivi di qualita' (iniziali):**

- nessun errore ruff/mypy nei file principali (`src/`),
- tutti i test verdi,
- coverage totale almeno **60%** (target futuro: 80–90%).

```

3. Salva il file.

**Checklist**
- [ ] Il README documenta chiaramente gli strumenti di qualità e la CI
- [ ] Ci sono comandi concreti che puoi copiare/incollare


---

### 2. Giro finale Fase 24

1. In locale:

```bash
tasks.bat quality
```

2. Su GitHub (dopo un eventuale `git push`), verifica che il workflow **CI** sia verde.

3. Se tutto è ok, crea (o aggiorna) un commit di chiusura per la Fase 24
   (se non l’hai già fatto nel Giorno 5).

**Checklist (fine Giorno 6 – fine Fase 24)**
- [ ] Script `tasks.bat` funzionante
- [ ] CI GitHub attiva e verde
- [ ] README aggiornato con sezione DevOps & Qualità
- [ ] Puoi lanciare tutti i check con un singolo comando (`tasks.bat quality`)
