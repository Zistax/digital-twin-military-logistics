# Fase 11 – Qualità & DevOps locale (Parte 2, Giorni 4–6, Windows)

> **Scopo Parte 2**  
> Spingere un po’ più in là l’idea di “DevOps locale”:
>
> - introdurre una **soglia minima di coverage**,
> - aggiungere un controllo di sicurezza base sulle dipendenze (`pip-audit`),
> - documentare nel README il tuo flusso qualità quotidiano.

> **Prerequisiti**:
> - Parte 1 completata (`fase11_1.md`),
> - `run_quality.bat` funziona,
> - hai già eseguito almeno una volta Ruff, Black e pytest‑cov.


---

## Struttura Parte 2

- **Giorno 4** – Aggiungere `pip-audit` e un file `pytest.ini` per coverage
- **Giorno 5** – Integrare `pip-audit` in uno script `run_security.bat` (o dentro `run_quality.bat`)
- **Giorno 6** – Aggiornare README, fare giro completo di qualità e commit Git


---

## Giorno 4 – `pip-audit` + configurazione coverage (`pytest.ini`)

### Obiettivo del giorno
- Installare **pip-audit** per controllare vulnerabilità note nelle dipendenze,
- creare un file `pytest.ini` con impostazioni di coverage e, se vuoi, una prima soglia.

> Non puntiamo subito al 90% di coverage: l’idea è **abituarsi** ad avere una soglia e ad alzarla piano piano.


---

### 1. Aggiungere `pip-audit` a `requirements.txt`

1. Apri `requirements.txt`.
2. Aggiungi (se non c’è già):

```txt
pip-audit
```

3. Salva il file.

**Checklist**
- [x] `requirements.txt` contiene `pip-audit`


---

### 2. Installare `pip-audit`

Nel terminale (con `.venv` attivo), dalla root del progetto:

```bash
pip install -r requirements.txt
```

Poi verifica velocemente:

```bash
pip-audit --help
```

**Checklist**
- [x] `pip-audit` è installato e risponde a `--help`


---

### 3. Creare `pytest.ini` per configurare coverage

1. Nella root del progetto, crea un file chiamato `pytest.ini` (se non esiste già).
2. Inserisci questo contenuto base:

```ini
[pytest]
addopts = --cov=src --cov-report=term-missing
testpaths = tests
```

> Questo fa sì che **anche se lanci solo `pytest`**, vengano comunque calcolata la coverage e mostrato cosa manca.

3. (Opzionale, ma utile) Aggiungi anche una soglia minima di coverage, ad esempio **60%** per iniziare (valore molto prudente):

```ini
[pytest]
addopts = --cov=src --cov-report=term-missing --cov-fail-under=60
testpaths = tests
```

> Se la coverage scende sotto 60%, `pytest` uscirà con errore.  
> Più avanti, quando avrai più test, potrai alzare gradualmente questa soglia (70, 80, …).

4. Salva `pytest.ini`.

**Checklist**
- [x] Esiste `pytest.ini` nella root con `addopts` che includono `--cov`
- [x] (Se vuoi) hai impostato una soglia `--cov-fail-under=60` o un altro valore


---

### 4. Verificare che `pytest` usi la nuova config

Nel terminale (con `.venv` attivo):

```bash
pytest
```

Dovresti vedere:

- l’esecuzione dei test,
- un report coverage simile a quello di prima,
- se la coverage è sotto la soglia, il comando restituisce errore (code != 0).

> Se al momento il progetto ha pochi test e la coverage è molto bassa, puoi iniziare con una soglia anche **40%** o **30%**. L’importante è che esista una **barriera minima**.

**Checklist (fine Giorno 4)**
- [x] `pytest` legge `pytest.ini` e mostra la coverage
- [x] Hai una soglia minima di coverage, anche se bassa (es. 40–60%)  


---

## Giorno 5 – Script `run_security.bat` e integrazione con `run_quality.bat`

### Obiettivo del giorno
- Creare uno script separato per i controlli di sicurezza (`run_security.bat`),
- opzionalmente richiamarlo alla fine di `run_quality.bat`.


---

### 1. Creare `run_security.bat`

1. Nella root del progetto, crea un file `run_security.bat`.
2. Inserisci questo contenuto:

```bat
@echo off
echo ==============================
echo Attivo l'ambiente virtuale...
echo ==============================

call .venv\Scripts\activate.bat

if errorlevel 1 (
    echo ERRORE: impossibile attivare l'ambiente .venv
    pause
    exit /b 1
)

echo.
echo ==============================
echo Controllo vulnerabilita' nelle dipendenze (pip-audit)...
echo ==============================

pip-audit

if errorlevel 1 (
    echo.
    echo ATTENZIONE: pip-audit ha trovato potenziali vulnerabilita'.
    echo Leggi bene l'output sopra e valuta se aggiornare alcune dipendenze.
) else (
    echo Nessuna vulnerabilita' nota trovata nelle dipendenze.
)

echo.
echo Controllo sicurezza completato.
echo ==============================

pause
```

3. Salva il file.

**Checklist**
- [x] Esiste `run_security.bat` nella root del progetto
- [x] Lo script attiva `.venv` e lancia `pip-audit`


---

### 2. Eseguire `run_security.bat` una prima volta

1. Doppio click su `run_security.bat` (oppure lancialo da terminale).
2. Osserva l’output:
   - se non ci sono vulnerabilità note → meglio così,
   - se ce ne sono, vedrai pacchetto + versione + suggerimenti.

> **Importante**: non è obbligatorio **subito** aggiornare tutto.  
> Segnati almeno i pacchetti più critici (segnalati da pip‑audit) e potrai pianificare un aggiornamento in una fase futura.

**Checklist**
- [x] Ho eseguito `run_security.bat` almeno una volta
- [x] Ho visto se ci sono vulnerabilità segnalate


---

### 3. (Opzionale) Richiamare `run_security.bat` da `run_quality.bat`

Se vuoi avere un **“super comando”** che fa tutto (qualità + sicurezza), puoi alla fine di `run_quality.bat` aggiungere:

```bat
echo.
echo Vuoi eseguire anche i controlli di sicurezza (pip-audit)? [S/N]
set /p RUNSEC=

if /I "%RUNSEC%"=="S" (
    call run_security.bat
) else (
    echo Salto i controlli di sicurezza.
)
```

In questo modo, dopo Ruff, Black e pytest, ti verrà chiesto se vuoi lanciare anche `pip-audit`.

Salva `run_quality.bat` se lo modifichi.

**Checklist (fine Giorno 5)**
- [x] Ho uno script `run_security.bat` separato
- [x] (Se voglio) `run_quality.bat` può richiamare `run_security.bat` alla fine


---

## Giorno 6 – README, giro completo e commit Fase 11

### Obiettivo del giorno
- Documentare nel `README.md` il flusso di qualità che vuoi usare,
- eseguire un giro completo di:
  - `run_quality.bat`
  - `run_security.bat`
- creare un commit Git per chiudere la Fase 11.


---

### 1. Aggiornare il README con la sezione “Qualità & sicurezza locale”

Apri `README.md` e aggiungi una sezione, ad esempio:

```markdown
## Qualita' & Sicurezza (uso locale)

Per mantenere il progetto in buona salute è disponibile una serie di comandi:

### Controlli di qualita'

- Script Windows:

  ```bat
  run_quality.bat
  ```

Questo script:
- attiva l'ambiente `.venv`,
- esegue il linting con **Ruff** (`ruff check src tests`),
- controlla la formattazione con **Black** (`black --check src tests`),
- esegue i test con coverage (`pytest` con impostazioni da `pytest.ini`).

La coverage minima è configurata tramite `pytest.ini` (opzione `--cov-fail-under`):
se la coverage scende sotto la soglia, i test falliscono.

### Controlli di sicurezza

- Script Windows:

  ```bat
  run_security.bat
  ```

Questo script attiva `.venv` ed esegue:

- `pip-audit` per controllare se alcune dipendenze hanno vulnerabilita' note.

In caso di vulnerabilita', valuta l'aggiornamento delle versioni interessate.
```

Adatta il testo se hai scelto soglie diverse o vuoi aggiungere altro.

Salva il `README.md`.

**Checklist**
- [x] Il README spiega come usare `run_quality.bat` e `run_security.bat`


---

### 2. Giro completo di qualità

Nel corso della giornata (o quando hai un po’ di tempo), esegui nell’ordine:

1. `run_quality.bat`
2. `run_security.bat` (se non già richiamato dal primo)

Osserva:

- quanti avvisi Ruff rimangono,
- se Black segnala ancora formattazioni da sistemare,
- che valore di coverage hai,
- se pip‑audit segnala vulnerabilità.

> Non devi per forza “risolvere tutto” subito.  
> Ma avere questo **cruscotto locale** ti aiuta a capire dove intervenire pian piano.

**Checklist**
- [ ] Ho lanciato `run_quality.bat` e visto output di Ruff, Black, pytest‑cov
- [ ] Ho lanciato `run_security.bat` e visto output di `pip-audit`


---

### 3. Commit Git di fine Fase 11

Nel terminale, dalla root del progetto:

```bash
git status
```

Dovresti vedere tra i file nuovi/modificati:

- `pyproject.toml`
- `pytest.ini`
- `run_quality.bat`
- `run_security.bat`
- `requirements.txt` (aggiornato)
- `README.md` (aggiornato)

1. Aggiungi i file:

```bash
git add .
```

2. Crea il commit con un messaggio chiaro, ad esempio:

```bash
git commit -m "Fase 11: quality gates locali (ruff/black, coverage, pip-audit)"
```

3. Verifica che il working tree sia pulito:

```bash
git status
```

Dovresti vedere: `nothing to commit, working tree clean`.

**Checklist (fine Giorno 6 – fine Fase 11)**
- [ ] Gli script `run_quality.bat` e `run_security.bat` funzionano
- [ ] Esiste `pytest.ini` con una soglia minima di coverage
- [ ] Il README documenta il flusso qualità/sicurezza
- [ ] Ho creato un commit Git per la Fase 11


---

## Fine Fase 11 – Cosa hai ottenuto

Con la Fase 11 hai dato al progetto una **prima vera base di DevOps locale**:

- comandi unificati per controllare qualità e sicurezza,
- linting + formattazione standardizzati,
- coverage con soglia minima,
- documentazione nel README per ricordarti il flusso.

Questo ti avvicina al tipo di “quality gates” descritti nei documenti più avanzati (coverage alta, sicurezza, ecc.), ma in una versione compatibile con il tuo contesto: **Windows, sviluppatore singolo, 2 ore al giorno**.

Nelle fasi successive, se vorrai, potremo:

- aggiungere un **workflow CI (GitHub Actions)** che esegue gli stessi controlli in remoto,
- introdurre strumenti più avanzati (mypy, bandit, ecc.),
- o passare ad altre parti del progetto (estensione del simulatore, nuove metriche, scenari aggiuntivi, ecc.).
