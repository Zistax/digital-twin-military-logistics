# Fase 16 – CI qualità estesa (Parte 2, Giorni 4–6, Windows)

> **Obiettivo pratico (Parte 2)**  
> Estendere la CI base per includere:
>
> - linting (Ruff),
> - formattazione (Black in modalità `--check`),
> - coverage (usando le opzioni già in `pytest.ini`),
> - un controllo rapido di sicurezza delle dipendenze (`pip-audit`) opzionale.

> L’idea è avvicinare il comportamento della CI a quello del tuo `run_quality.bat`.


---

## Struttura Fase 16 – Parte 2

- **Giorno 4** – Estendere il job di test per includere Ruff, Black, pytest con coverage
- **Giorno 5** – Aggiungere un job opzionale di sicurezza con `pip-audit`
- **Giorno 6** – Documentare la CI nel README, fare un giro completo e committare


---

## Giorno 4 – Linting & formattazione in CI

### Obiettivo del giorno
- Fare in modo che la CI fallisca se:
  - Ruff trova problemi seri,
  - Black rileva file non formattati (`--check`),
  - `pytest` fallisce o la coverage è sotto la soglia (gestita da `pytest.ini`).


---

### 1. Verificare che `ruff`, `black`, `pytest-cov` e `pip-audit` siano nei requirements

1. Apri `requirements.txt`.
2. Controlla che contenga queste righe (aggiungi se mancano):

```txt
black
ruff
pytest-cov
pip-audit
```

3. Salva il file.

> In locale hai già installato questi tool nelle fasi precedenti;
> la CI li installerà automaticamente con `pip install -r requirements.txt`.

**Checklist**
- [ ] `requirements.txt` contiene black, ruff, pytest-cov, pip-audit


---

### 2. Aggiornare `.github/workflows/ci.yml` per includere Ruff e Black

1. Apri `.github/workflows/ci.yml`.
2. Modifica il job `tests` per aggiungere degli step, ad esempio così:

```yaml
name: CI

on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]

jobs:
  tests:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Lint con Ruff
        run: |
          ruff check src tests

      - name: Controllo formattazione con Black
        run: |
          black --check src tests

      - name: Run tests with pytest (con coverage da pytest.ini)
        run: |
          pytest
```

3. Salva il file.

> Se `pytest.ini` contiene già `--cov` e `--cov-fail-under`, la coverage sarà
> verificata automaticamente anche in CI.

**Checklist**
- [ ] Il workflow ora ha step per Ruff, Black e pytest


---

### 3. Commit + push e verifica run CI

1. Nel terminale, dalla root del progetto:

```bash
git add .github/workflows/ci.yml requirements.txt
git commit -m "Estende CI con Ruff, Black e coverage"
git push
```

2. Vai su GitHub → tab **Actions** → workflow **CI**.
3. Verifica che i nuovi step:

   - “Lint con Ruff”,
   - “Controllo formattazione con Black”,
   - “Run tests with pytest (con coverage da pytest.ini)”

   siano **verdi** (o individua eventuali problemi).

**Checklist (fine Giorno 4)**
- [ ] La CI ora esegue Ruff, Black e pytest con coverage
- [ ] Sai interpretare errori di Ruff/Black nel log CI


---

## Giorno 5 – Job opzionale di sicurezza con `pip-audit`

### Obiettivo del giorno
- Aggiungere un secondo job che esegue `pip-audit` sui requirements,
- non bloccare necessariamente la CI se trova vulnerabilità (almeno all’inizio).


---

### 1. Aggiungere il job `security` in `ci.yml`

1. Apri `.github/workflows/ci.yml`.
2. Sotto il job `tests`, aggiungi un secondo job `security`:

```yaml
  security:
    runs-on: ubuntu-latest
    needs: tests   # il job security parte dopo che i test sono passati

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Controllo vulnerabilita' con pip-audit (non bloccante)
        continue-on-error: true
        run: |
          pip-audit
```

3. Salva il file.

> `continue-on-error: true` fa sì che, anche se `pip-audit` trova vulnerabilità,
> il job venga segnato come “giallo” (warning) ma non blocchi l’intera CI.
> In futuro potrai togliere questa opzione se vuoi essere più rigido.

**Checklist**
- [ ] Esiste un job `security` in `ci.yml` che esegue pip-audit


---

### 2. Commit + push e controllo del job security

1. Nel terminale:

```bash
git add .github/workflows/ci.yml
git commit -m "Aggiunge job sicurezza con pip-audit in CI"
git push
```

2. Su GitHub → tab **Actions** → workflow **CI**:
   - dovresti vedere due job: `tests` e `security`,
   - controlla i log di `security` per vedere se `pip-audit` segnala qualcosa.

> Se ci sono vulnerabilità, GitHub ti mostrerà la lista dei pacchetti interessati
> e le versioni suggerite. Potrai pianificare aggiornamenti in una fase futura.


**Checklist (fine Giorno 5)**
- [ ] Il job `security` gira dopo i test
- [ ] Vedi l’output di `pip-audit` nella CI


---

## Giorno 6 – Documentare la CI, giro completo e commit finale

### Obiettivo del giorno
- Aggiornare il `README.md` con una sezione dedicata alla CI,
- fare un giro “pulito” (run CI verde),
- chiudere la Fase 16 con un commit chiaro.


---

### 1. Aggiornare README con sezione “CI & Quality Gates”

Apri `README.md` e aggiungi (o estendi) una sezione, ad esempio:

```markdown
## CI & Quality Gates

Il repository include una pipeline CI basata su **GitHub Actions** (`.github/workflows/ci.yml`)
che viene eseguita ad ogni push e pull request sul branch `main`.

La pipeline esegue:

- linting con **Ruff**:
  - `ruff check src tests`
- controllo formattazione con **Black** (solo check):
  - `black --check src tests`
- test automatici con **pytest** (coverage e soglia definiti in `pytest.ini`)
- job opzionale di sicurezza con **pip-audit**:
  - installa i requirements e lancia `pip-audit` (per ora non bloccante).

In locale sono disponibili script analoghi (`run_quality.bat`, `run_security.bat`)
per eseguire gli stessi controlli prima di fare push.
```

Adatta i nomi se hai personalizzato gli script.

Salva il `README.md`.

**Checklist**
- [ ] Il README descrive in modo chiaro cosa fa la CI


---

### 2. Giro completo di verifica (locale + remoto)

1. In locale (facoltativo ma consigliato), lancia:

```bash
run_quality.bat
run_security.bat
```

Assicurati che non ci siano errori gravi (o almeno capisci cosa manca).

2. Fai una piccola modifica a un file di testo (es. `README.md`), poi:

```bash
git add README.md
git commit -m "Aggiorna README con sezione CI & Quality Gates"
git push
```

3. Su GitHub → tab **Actions**:
   - verifica che sia partito un nuovo run del workflow **CI**,
   - controlla che **entrambi** i job (`tests` e `security`) vadano a buon fine
     (anche se `security` può segnare warning per vulnerabilità).

**Checklist**
- [ ] L’ultimo run CI su GitHub è verde (o ha solo warning nel job security)
- [ ] Sei in grado di leggere lo stato della CI direttamente dal badge nel README (se lo hai aggiunto)


---

### 3. Fine Fase 16 – Stato Git e ordine del repository

Nel terminale, dalla root del progetto:

```bash
git status
```

Dovresti vedere: `nothing to commit, working tree clean`.

Se ci sono file non tracciati (es. CSV di output, cartelle locali), valuta se:

- aggiungerli a `.gitignore`,
- oppure committarli se ha senso (di solito **no** per output di simulazioni).

**Checklist (fine Giorno 6 – fine Fase 16)**
- [ ] Workflow CI esteso creato e funzionante
- [ ] CI esegue lint, format check, test + coverage e pip-audit
- [ ] README aggiornato con sezione CI & Quality Gates
- [ ] Repository Git pulito e allineato con GitHub


---

Con la Fase 16 hai portato il tuo progetto a un livello superiore di **DevOps**:

- ogni push viene validato automaticamente da test, lint e format,
- hai un controllo continuo sulle dipendenze (`pip-audit`),
- la documentazione spiega chiaramente cosa fa la CI.

Questo ti aiuta a mantenere il progetto sano nel tempo, anche se lo estenderai con
nuove feature, nuove pipeline dati o componenti RL più complessi.
