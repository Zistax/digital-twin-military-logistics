# Fase 16 – CI base con GitHub Actions (Parte 1, Giorni 1–3, Windows)

> **Obiettivo pratico (Parte 1)**  
> Portare i controlli che hai già in locale (test, qualità base) anche **in remoto**,
> usando **GitHub Actions** come CI minima:
>
> - avere una pipeline che gira ad ogni push/pull request,
> - installa le dipendenze,
> - esegue i test (`pytest`).

> **Nota:** se non usi GitHub puoi adattare facilmente questi passi ad altri servizi
> (GitLab CI, Azure DevOps, ecc.), ma in questa fase useremo GitHub come riferimento.

---

## Struttura Fase 16 – Parte 1

- **Giorno 1** – Preparare il repository remoto su GitHub
- **Giorno 2** – Creare il workflow CI base (`.github/workflows/ci.yml`)
- **Giorno 3** – Verifica del workflow + badge opzionale nel README

---

## Giorno 1 – Preparare il repository remoto su GitHub

### Obiettivo del giorno
- Avere il tuo progetto su un repository remoto (GitHub),
- collegare il repository locale (sul tuo PC Windows) a quello remoto.

> Se hai già fatto tutto questo, puoi limitarti a controllare che il remote sia configurato
> e passare direttamente al Giorno 2.

---

### 1. Creare un repository vuoto su GitHub

1. Vai su <https://github.com> e accedi con il tuo account.
2. In alto a destra clicca sul pulsante **“+” → New repository**.
3. Compila:
   - **Repository name**: ad esempio `digital-twin-logistico` (o come preferisci),
   - **Visibility**: `Private` o `Public` (come preferisci),
   - **Initialize this repository with**: **NON** spuntare `Add a README`, `Add .gitignore`, ecc. (meglio vuoto).
4. Clicca su **Create repository**.
5. GitHub ti mostrerà una pagina con le istruzioni `…or push an existing repository from the command line`.

Tieni aperta quella pagina: ti serviranno gli URL.

**Checklist**
- [ ] Esiste un repository vuoto su GitHub per il progetto


---

### 2. Collegare il repository locale a quello remoto

1. Sul tuo PC Windows, apri **PowerShell** o **cmd**.
2. Vai nella cartella del progetto:

```bash
cd C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico
```

3. Verifica che il repository Git locale esista già:

```bash
git status
```

Se **non** è un repo Git (messaggio tipo “not a git repository”), inizializzalo:

```bash
git init
git add .
git commit -m "Init progetto digital twin logistico"
```

4. Aggiungi il **remote** di GitHub (usa l’URL indicato nella pagina GitHub, tipo `https://github.com/USERNAME/digital-twin-logistico.git`):

```bash
git remote add origin https://github.com/USERNAME/digital-twin-logistico.git
```

5. Verifica che sia configurato:

```bash
git remote -v
```

6. Esegui il primo push (se non c’è ancora il branch `main`, crealo). Esempio:

```bash
git branch -M main
git push -u origin main
```

Potrebbe chiederti username/password o token; segui le istruzioni di GitHub per l’autenticazione.

**Checklist**
- [ ] `git remote -v` mostra l’URL del repository GitHub
- [ ] `git push -u origin main` è andato a buon fine


---

### 3. Verificare su GitHub

1. Torna sulla pagina del repository GitHub nel browser.
2. Aggiorna la pagina (`F5`):
   - dovresti vedere i file del tuo progetto (src, tests, conf, ecc.).

**Checklist (fine Giorno 1)**
- [ ] Il repository GitHub mostra tutti i file del progetto
- [ ] Sei pronto a definire un workflow CI in `.github/workflows`


---

## Giorno 2 – Workflow CI base (`.github/workflows/ci.yml`)

### Obiettivo del giorno
- Creare un **workflow GitHub Actions** che:
  - gira su `push` e `pull_request`,
  - usa un runner `ubuntu-latest`,
  - installa Python,
  - installa i requirements,
  - esegue `pytest`.


---

### 1. Creare la cartella `.github/workflows`

1. In **VS Code**, apri la root del progetto.
2. Crea una cartella `.github` (se non esiste):
   - clic destro → **New Folder** → `.github`
3. Dentro `.github`, crea una cartella `workflows`:
   - clic destro su `.github` → **New Folder** → `workflows`

La struttura deve risultare:

- `.github/workflows`

**Checklist**
- [ ] Esiste `.github/workflows` nella root del progetto


---

### 2. Creare il file `ci.yml`

1. In `\.github\workflows`, crea un nuovo file:

   - `ci.yml`

2. Inserisci questo contenuto di base (puoi copiare/incolare):

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

      - name: Run tests with pytest
        run: |
          pytest
```

3. Salva il file.

> Questo workflow è minimale ma già utile: ogni volta che fai push o apri una PR
> sul branch `main`, girerà automaticamente `pytest` su Ubuntu.

**Checklist**
- [ ] Esiste `.github/workflows/ci.yml` con il job `tests` che esegue `pytest`


---

### 3. Commit e push del workflow

1. Nel terminale (ancora nella root del progetto):

```bash
git status
```

Dovresti vedere `.github/workflows/ci.yml` tra i file “untracked” o “modified”.

2. Aggiungi e committa:

```bash
git add .github/workflows/ci.yml
git commit -m "Aggiunge workflow CI base con pytest"
```

3. Fai il push:

```bash
git push
```

**Checklist (fine Giorno 2)**
- [ ] Il commit con il workflow CI è su GitHub
- [ ] GitHub Actions inizierà a girare al prossimo push


---

## Giorno 3 – Verificare il workflow + badge nel README (opzionale)

### Obiettivo del giorno
- Verificare che il workflow CI **giri e passi**,
- aggiungere (facoltativo) un **badge di status** nel README.

---

### 1. Forzare un run della CI

1. Fai una piccola modifica a un file di testo (es. `README.md`):
   - aggiungi una riga vuota o una frase breve.
2. Salva il file.
3. Nel terminale:

```bash
git add README.md
git commit -m "Trigger CI dopo aggiunta workflow"
git push
```

4. Vai su GitHub, pagina del repository.
5. Clicca sulla tab **“Actions”** (in alto).
6. Dovresti vedere un workflow chiamato **“CI”** con un run in corso.

   - Clicca sul run per vedere i log,
   - verifica che i passi:
     - “Set up Python”,
     - “Install dependencies”,
     - “Run tests with pytest”
     siano andati a buon fine (spunta verde).

> Se i test falliscono, guarda il log per capire quale test è in errore.
> È normale dover correggere qualcosa la prima volta.

**Checklist**
- [ ] Vedi almeno un run del workflow “CI” nella tab Actions
- [ ] Il job `tests` è verde (o sai quale test fallisce e perché)


---

### 2. (Opzionale) Aggiungere il badge di build status al README

1. Nella pagina **Actions → workflow “CI”**, GitHub mostra un menu `...` o `Create status badge`.
2. Copia il markdown del badge fornito da GitHub, che sarà simile a:

```markdown
[![CI](https://github.com/USERNAME/digital-twin-logistico/actions/workflows/ci.yml/badge.svg)](https://github.com/USERNAME/digital-twin-logistico/actions/workflows/ci.yml)
```

3. Apri `README.md` in VS Code.
4. Incolla il badge nella parte alta del file, ad esempio subito sotto il titolo principale:

```markdown
# Digital Twin Logistico

[![CI](https://github.com/USERNAME/digital-twin-logistico/actions/workflows/ci.yml/badge.svg)](https://github.com/USERNAME/digital-twin-logistico/actions/workflows/ci.yml)

...
```

5. Salva il file.
6. Commit + push:

```bash
git add README.md
git commit -m "Aggiunge badge CI al README"
git push
```

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] Il workflow CI base gira ed esegue `pytest` ad ogni push/PR
- [ ] (Opzionale) Il README mostra un badge CI funzionante
- [ ] Sai dove guardare i log in caso di errore (tab Actions su GitHub)
