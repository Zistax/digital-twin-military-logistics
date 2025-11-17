# Fase 11 – Qualità & DevOps locale (Parte 1, Giorni 1–3, Windows)

> **Scopo Fase 11 (visione generale)**  
> Iniziare a dare al progetto delle **“quality gate”** da sviluppatore singolo:
>
> - avere un comando unico che lancia test + coverage,
> - introdurre **formatter** (Black) e **linter** (Ruff) per tenere il codice pulito,
> - abituarti a un flusso tipo “pre‑commit” anche solo locale (su Windows, con `.bat`).  
>
> In **Parte 1** prepari gli strumenti e un primo script di controllo.  
> In **Parte 2** (file `fase11_2`) aggiungerai security check base e una soglia di coverage.

> **Prerequisiti:**
> - Fino alla Fase 10 completata,
> - `pytest` funziona,
> - usi Git per versionare il progetto.


---

## Struttura Fase 11 – Parte 1

- **Giorno 1** – Aggiungere tool di qualità: `black`, `ruff`, `pytest-cov`
- **Giorno 2** – Creare configurazione base (pyproject) per Black/Ruff
- **Giorno 3** – Creare uno script `run_quality.bat` e primo giro di fix


---

## Giorno 1 – Aggiungere Black, Ruff, pytest‑cov

### Obiettivo del giorno
- Installare tre strumenti fondamentali:
  - **Black** (formatter),
  - **Ruff** (linter veloce),
  - **pytest‑cov** (per misurare la coverage dei test).


---

### 1. Aggiornare `requirements.txt`

1. Apri **VS Code**.
2. Apri `requirements.txt` (root del progetto).
3. Aggiungi queste righe (se non sono già presenti):

```txt
black
ruff
pytest-cov
```

> Se preferisci, puoi commentare `black` e `ruff` con `#` per ora, ma ti consiglio di tenerli attivi.

4. Salva il file (`Ctrl + S`).

**Checklist**
- [ ] `requirements.txt` contiene `black`, `ruff`, `pytest-cov`


---

### 2. Installare i tool nell’ambiente `.venv`

1. Apri **PowerShell** o **cmd**.
2. Vai nella cartella del progetto (sostituisci `TUO_UTENTE`):

```bash
cd C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico
```

3. Attiva l’ambiente virtuale `.venv`:

- PowerShell:

  ```bash
  .venv\Scripts\Activate.ps1
  ```

- cmd:

  ```bat
  .venv\Scripts\activate.bat
  ```

4. Installa/aggiorna i pacchetti:

```bash
pip install -r requirements.txt
```

5. Verifica velocemente che i comandi siano visibili:

```bash
black --version
ruff --version
pytest --version
```

**Checklist (fine Giorno 1)**
- [ ] Ambiente `.venv` attivo
- [ ] `pip install -r requirements.txt` completato
- [ ] `black --version` e `ruff --version` funzionano senza errore


---

## Giorno 2 – Configurare Black & Ruff con `pyproject.toml`

### Obiettivo del giorno
- Creare un file di configurazione unico (`pyproject.toml`) per:
  - Black (formatter),
  - Ruff (linter),
- impostare regole semplici per non impazzire con warning inutili.


---

### 1. Creare (o aggiornare) `pyproject.toml`

1. In **VS Code**, nella root del progetto, controlla se esiste già `pyproject.toml`.
   - Se **non esiste**, crealo nuovo.
   - Se esiste, aggiungerai solo le sezioni mancanti.

2. Inserisci/aggiungi questo contenuto base:

```toml
[tool.black]
line-length = 88
target-version = ["py311"]
include = "\.pyi?$"
exclude = """
/(
    \.git
  | \.venv
  | build
  | dist
  | data
  | models
)/
"""

[tool.ruff]
line-length = 88
target-version = "py311"
exclude = [
    ".git",
    ".venv",
    "build",
    "dist",
    "data",
    "models",
]

# Attiviamo un set base di regole (leggere) per iniziare
select = ["E", "F"]
ignore = []

[tool.ruff.format]
# Per compatibilità con black style (se in futuro vuoi usare ruff format)
quote-style = "double"
```

> `select = ["E", "F"]` attiva solo errori veri (E) e problemi di tipo “flake” (F).  
> Più avanti puoi aggiungere altre famiglie (es. `"W"`, `"I"`, `"N"`, ecc.).

3. Salva il file.

**Checklist**
- [ ] Esiste `pyproject.toml` nella root del progetto
- [ ] Sezioni `[tool.black]` e `[tool.ruff]` sono presenti


---

### 2. Prima prova manuale di Ruff e Black (solo “dry run”)

Per non fare subito cambiamenti, puoi far girare Ruff e Black in modalità “controllo”:

Nel terminale (con `.venv` attivo):

```bash
ruff check src tests
```

Osserva gli output: saranno numerati tipo `E302`, `F401`, ecc.

Poi prova Black in “diff mode” (mostra cosa cambierebbe senza modificare i file):

```bash
black --diff src tests
```

Non è necessario sistemare tutto oggi: l’obiettivo è **vedere** la quantità di interventi.

**Checklist (fine Giorno 2)**
- [ ] Ho lanciato `ruff check src tests` almeno una volta
- [ ] Ho lanciato `black --diff src tests` per capire il tipo di modifiche suggerite
- [ ] Ho un’idea di quante cose andranno sistemate (anche con calma nel tempo)


---

## Giorno 3 – Script `run_quality.bat` e primo giro di fix

### Obiettivo del giorno
- Creare uno script unico **Windows** (`run_quality.bat`) che:
  - attiva il virtualenv,
  - lancia Ruff,
  - lancia Black in modalità “check”,
  - lancia `pytest` con coverage,
- fare un primo giro di fix su errori semplici.


---

### 1. Creare `run_quality.bat`

1. Nella root del progetto, crea un nuovo file chiamato:

   - `run_quality.bat`

2. Inserisci questo contenuto (puoi adattare qualche messaggio):

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
echo Linting con Ruff...
echo ==============================

ruff check src tests
if errorlevel 1 (
    echo.
    echo ATTENZIONE: Ruff ha trovato problemi.
    echo Controlla i messaggi sopra (E/F) e correggili.
) else (
    echo Nessun problema trovato da Ruff.
)

echo.
echo ==============================
echo Controllo formattazione con Black (senza modificare i file)...
echo ==============================

black --check src tests
if errorlevel 1 (
    echo.
    echo ATTENZIONE: Black suggerisce modifiche di formattazione.
    echo Per applicarle automaticamente esegui:
    echo   black src tests
) else (
    echo Formattazione OK secondo Black.
)

echo.
echo ==============================
echo Test con coverage (pytest-cov)...
echo ==============================

pytest --cov=src --cov-report=term-missing

echo.
echo ==============================
echo Controlli di qualita' completati.
echo ==============================

pause
```

3. Salva il file.

**Checklist**
- [ ] Esiste `run_quality.bat` nella root del progetto
- [ ] Lo script attiva `.venv`, lancia Ruff, Black (check) e `pytest --cov`


---

### 2. Eseguire `run_quality.bat` la prima volta

1. Dal **File Explorer**:
   - vai nella cartella del progetto,
   - fai doppio click su `run_quality.bat`  
     (oppure apri un terminale e lancia `run_quality.bat`).

2. Osserva l’output:
   - **Ruff** probabilmente segnalerà diversi errori/avvisi,
   - **Black** potrebbe segnalare che la formattazione non è allineata,
   - `pytest --cov` genererà l’output dei test con coverage.

> Per ora **non** è obbligatorio arrivare a 0 problemi.  
> L’obiettivo è avere un comando unico per vedere lo **stato di salute** del progetto.

**Checklist**
- [ ] Ho eseguito `run_quality.bat` almeno una volta
- [ ] Vedo output di Ruff, Black e pytest con coverage


---

### 3. Primo giro di fix “soft”

Per non scoraggiarti, oggi correggi solo problemi semplici, ad esempio:

- import inutilizzati (`F401`),
- variabili non usate,
- errori di indentazione veri (`E`),
- piccoli dettagli che Ruff ti segnala e che capisci facilmente.

**Strategia consigliata**:

1. Scegli **un file** alla volta (es. `src/sim/main_sim.py`).
2. Applica le correzioni suggerite da Ruff per quel file (o solo una parte).
3. (Facoltativo) lancia Black solo su quel file:

   ```bash
   black src\sim\main_sim.py
   ```

4. Rilancia `run_quality.bat` e vedi se i messaggi diminuiscono.

> Non serve “pulire tutto” in un colpo solo.  
> L’importante è **creare l’abitudine** e vedere progressi graduali.

**Checklist (fine Giorno 3)**
- [ ] `run_quality.bat` funziona e mostra Ruff + Black + pytest-cov
- [ ] Ho corretto almeno alcuni problemi segnalati da Ruff
- [ ] Ho eventualmente formattato 1–2 file con Black per fare pratica


---

## Fine Parte 1 – Cosa hai ora

Alla fine di questa Parte 1 della Fase 11 hai:

- una base di tool di qualità:
  - **Ruff** per il linting,
  - **Black** per la formattazione,
  - **pytest‑cov** per la coverage;
- un file di configurazione unico (`pyproject.toml`) per Black e Ruff,
- uno script `run_quality.bat` che lancia tutto con un doppio click.

Nella **Parte 2** (`fase11_2.md`) farai un passo in più verso le **quality gate**:

- aggiungerai una **soglia minima di coverage** (anche bassa all’inizio),
- introdurrai un check di sicurezza base con `pip-audit`,
- aggiornerai il README per ricordarti il flusso quotidiano di qualità.
