# Fase 01 – Setup ambiente & progetto (Windows, dettaglio per giornate)

> **Scopo della Fase 01**  
> Preparare il tuo PC Windows, l’ambiente Python e la struttura base del progetto in modo che tu possa iniziare a sviluppare il simulatore e il resto del sistema senza problemi, lavorando circa **2 ore al giorno**.

La fase è divisa in **5 giornate di lavoro** (Giorno 1 → Giorno 5).  
Ogni giornata ha:
- un **obiettivo chiaro**
- una **checklist di passi da fare**
- una **verifica finale veloce**

Se un giorno non finisci tutto, **continua il giorno dopo**: non è un problema.

---

## Giorno 1 – Installare gli strumenti di base (Windows)

### Obiettivo del giorno
Avere installati e funzionanti su Windows:
- **Python 3**  
- **Git**  
- **Visual Studio Code (VS Code)**  
- (Opzionale) un account **GitHub**

---

### 1. Aprire il terminale su Windows

Userai due tipi di terminale:
- **Prompt dei comandi (cmd)**
- oppure **PowerShell**

Per aprire rapidamente PowerShell:
- premi **Win + X**
- scegli **“Windows PowerShell”** o **“Terminale Windows”**

> Nei comandi seguenti puoi usare sia cmd che PowerShell.  
> Se c’è differenza, lo specifico.

---

### 2. Verificare / installare Python 3

1. Nel terminale (cmd o PowerShell), prova questi comandi **uno alla volta**:
   - `py --version`  
   - se non funziona, prova: `python --version`

2. Se vedi qualcosa del tipo:
   - `Python 3.x.x` → **OK, Python è già installato** ✔

3. Se ricevi un errore tipo “comando non riconosciuto”, Python non è installato oppure non è nel PATH.

   - Apri il browser e vai sul sito ufficiale Python (cerca “Download Python Windows”)
   - Scarica l’installer di **Python 3.x** per Windows
   - Avvia l’installer
   - **Importante**: nella prima schermata, spunta la casella  
     **“Add Python 3.x to PATH”**
   - Prosegui con l’installazione standard
   - Chiudi il terminale, riaprilo
   - Riprova: `py --version` oppure `python --version`

**Checklist Python (Giorno 1)**  
- [x] Ho aperto il terminale (cmd o PowerShell)
- [x] `py --version` o `python --version` mostra una versione 3.x

---

### 3. Verificare / installare Git

1. Nel terminale, esegui:
   ```bash
   git --version
   ```
2. Se vedi qualcosa tipo `git version 2.x.x` → **Git è già installato** ✔  
3. Se vedi un errore:
   - Apri il browser e cerca “Download Git Windows”
   - Scarica l’installer dal sito ufficiale Git
   - Avvia l’installer e **lascia le opzioni predefinite**
   - Chiudi il terminale, riaprilo
   - Riprova: `git --version`

**Checklist Git (Giorno 1)**  
- [x] `git --version` mostra una versione valida

---

### 4. Installare Visual Studio Code

1. Apri il browser e cerca “Download VS Code Windows”
2. Scarica l’installer per Windows
3. Avvia l’installer e segui i passaggi (impostazioni predefinite vanno bene)
4. Avvia VS Code dal menu Start e verifica che si apra senza errori

**Checklist VS Code (Giorno 1)**  
- [x] VS Code si apre correttamente

---

### 5. (Opzionale) Creare un account GitHub

1. Apri il browser e vai su GitHub (cerca “GitHub”)
2. Clicca su **Sign up** / Registrati
3. Crea un account gratuito seguendo i passaggi

**Checklist GitHub (opzionale)**  
- [x] Ho creato un account GitHub (opzionale ma consigliato)

---

### Fine Giorno 1 – Verifica veloce

- [x] `py --version` o `python --version` funziona
- [x] `git --version` funziona
- [x] VS Code si avvia
- [x] (Opzionale) Ho un account GitHub

Se tutte (o quasi tutte) le caselle sono spuntate, puoi passare al Giorno 2.

---

## Giorno 2 – Cartella progetto, Git e ambiente virtuale (Windows)

### Obiettivo del giorno
- Creare la **cartella del progetto** sul disco
- Inizializzare un **repository Git** locale
- Creare un **ambiente virtuale Python** (`.venv`)
- Creare un file `requirements.txt` e installare i pacchetti base

> Prima di iniziare, apri il **Terminale** (cmd o PowerShell).  
> Nei comandi userò esempi per PowerShell, ma vanno bene anche in cmd.

---

### 1. Scegliere dove creare il progetto

Scegli una cartella dove tenere i progetti, ad esempio:

- `C:\Users\TUO_UTENTE\Progetti\`

Nel terminale (sostituisci `TUO_UTENTE` con il tuo nome utente Windows):

```bash
cd C:\Users\TUO_UTENTE
mkdir Progetti
cd Progetti
```

**Checklist**  
- [x] Ho una cartella per i progetti (es. `C:\Users\TUO_UTENTE\Progetti\`)

---

### 2. Creare la cartella del progetto

1. Nel terminale, dentro la cartella `Progetti`, crea la cartella del progetto:

   ```bash
   mkdir digital-twin-logistico
   cd digital-twin-logistico
   ```

2. Conferma di essere dentro la cartella giusta mostrando il percorso corrente:

   ```bash
   cd
   ```

   oppure guarda il prompt (di solito mostra il percorso corrente).

**Checklist**  
- [x] La cartella `digital-twin-logistico` esiste
- [x] Sono dentro `C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico`

---

### 3. Inizializzare il repository Git

1. Nel terminale (sempre dentro `digital-twin-logistico`):

   ```bash
   git init
   ```

2. Controlla lo stato:

   ```bash
   git status
   ```

   Dovresti vedere qualcosa tipo:
   - `On branch master` o `On branch main`
   - `No commits yet`

**Checklist**  
- [x] Ho eseguito `git init` dentro la cartella del progetto
- [x] `git status` mi dice che sono su un branch (master/main)

---

### 4. Creare un file `.gitignore` di base (Windows)

1. Nella cartella `digital-twin-logistico`, crea un file chiamato `.gitignore`.  
   Puoi farlo in due modi:

   - da VS Code (consigliato):
     - apri VS Code
     - `File` → `Open Folder...` → seleziona `digital-twin-logistico`
     - nella barra laterale, clicca su **New File** e chiamalo `.gitignore`

   - opppure da terminale (PowerShell):
     ```bash
     ni .gitignore
     ```

2. Inserisci nel file `.gitignore` questo contenuto:

```gitignore
# Ambiente virtuale
.venv/
venv/

# File di cache Python
__pycache__/
*.py[cod]

# File temporanei editor
.vscode/
*.log

# Dati grezzi locali (opzionale, se non vuoi inviarli a GitHub)
data/raw/
```

**Checklist**  
- [x] Esiste un file `.gitignore` nella cartella del progetto
- [x] Il file contiene almeno le voci per `.venv/` e `__pycache__/`

---

### 5. Creare l’ambiente virtuale Python (.venv)

Nel terminale, assicurati di essere in `digital-twin-logistico`.

1. Esegui **UNO** dei seguenti comandi (quello che funziona meglio sul tuo PC):

   - Opzione 1 (consigliata se `py` funziona):
     ```bash
     py -3 -m venv .venv
     ```

   - Opzione 2 (se `python` funziona):
     ```bash
     python -m venv .venv
     ```

2. Dopo qualche secondo dovresti vedere nella cartella del progetto una cartella `.venv`.

3. **Attivare l’ambiente virtuale (PowerShell):**

   ```bash
   .venv\Scripts\Activate.ps1
   ```

   Se vedi un messaggio riguardo all’esecuzione degli script (Execution Policy), puoi:

   - chiudere e riaprire il terminale come **Amministratore**
   - eseguire (una sola volta):
     ```bash
     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned
     ```
   - poi riprovare:
     ```bash
     .venv\Scripts\Activate.ps1
     ```

4. **Attivare l’ambiente virtuale (cmd):**

   ```bat
   .venv\Scripts\activate.bat
   ```

5. Quando l’ambiente è attivo, il prompt del terminale mostra qualcosa tipo:
   - `(.venv) C:\Users\...\digital-twin-logistico>`

**Checklist**  
- [x] Esiste la cartella `.venv` dentro `digital-twin-logistico`
- [x] Riesco ad attivare l’ambiente con `.venv\Scripts\Activate.ps1` (PowerShell) o `activate.bat` (cmd)
- [x] Vedo `(.venv)` all’inizio della riga del terminale

---

### 6. Creare `requirements.txt` e installare i pacchetti

Con l’ambiente virtuale **attivo** (`(.venv)` nel prompt):

1. Crea il file `requirements.txt` nella cartella del progetto.  
   Contenuto iniziale consigliato:

```txt
numpy
pandas
matplotlib
jupyter
pytest
```

2. Salva il file.

3. Nel terminale (con `.venv` attivo), esegui:

```bash
pip install -r requirements.txt
```

4. Attendi che tutti i pacchetti vengano installati (può richiedere qualche minuto la prima volta).

**Checklist**  
- [x] Esiste un file `requirements.txt`
- [x] Ho eseguito `pip install -r requirements.txt` senza errori gravi

---

### Fine Giorno 2 – Verifica veloce

- [x] La cartella `digital-twin-logistico` esiste dentro la cartella dei Progetti
- [x] Ho inizializzato Git (`git init`)
- [x] Esiste `.gitignore` con `.venv/` e `__pycache__/`
- [x] Esiste la cartella `.venv`
- [x] Riesco ad attivare l’ambiente (`(.venv)` nel prompt)
- [x] I pacchetti di `requirements.txt` sono stati installati

Se è tutto OK, puoi proseguire al Giorno 3.

---

## Giorno 3 – Struttura cartelle del progetto (Windows)

### Obiettivo del giorno
Creare la **struttura delle cartelle** interne al progetto e un **README** iniziale.

Assicurati che l’ambiente virtuale `.venv` sia **attivo** (se non lo è, attivalo come al Giorno 2).

---

### 1. Creare le cartelle principali

Nel terminale, dentro `digital-twin-logistico`:

```bash
mkdir src
mkdir src\sim
mkdir src\ml
mkdir src\ui
mkdir data
mkdir data\raw
mkdir data\processed
mkdir notebooks
mkdir docs
mkdir tests
```

**Checklist**  
- [x] Esistono le cartelle: `src`, `data`, `notebooks`, `docs`, `tests`
- [x] Dentro `src` esistono: `sim`, `ml`, `ui`
- [x] Dentro `data` esistono: `raw`, `processed`

---

### 2. Rendere `src` un pacchetto Python

Per poter usare comandi tipo `python -m src.sim.main_sim`, `src` deve essere un “pacchetto” Python.

1. In VS Code (o altro editor), crea i seguenti file vuoti:
   - `src\__init__.py`
   - `src\sim\__init__.py`
   - `src\ml\__init__.py`
   - `src\ui\__init__.py`

2. I file possono essere anche completamente vuoti.

**Checklist**  
- [x] Esiste `src\__init__.py`
- [x] Esistono `__init__.py` in `src\sim`, `src\ml`, `src\ui`

---

### 3. Aprire il progetto in VS Code (se non hai già fatto)

1. Avvia **VS Code**
2. Vai su **File → Open Folder...**
3. Seleziona la cartella `digital-twin-logistico`
4. Nella barra laterale (Explorer) dovresti vedere:
   - `.venv` (può essere nascosta)
   - `src`, `data`, `notebooks`, `docs`, `tests`
   - file come `.gitignore`, `requirements.txt`

**Checklist**  
- [x] Il progetto è aperto in VS Code
- [x] Vedo tutte le cartelle nella barra laterale

---

### 4. Creare un `README.md` di base

1. Nella radice del progetto (`digital-twin-logistico`), crea il file `README.md`
2. Inserisci un contenuto iniziale, ad esempio:

```markdown
# Digital Twin Logistico – MVP (Windows)

Questo progetto ha l'obiettivo di creare un primo prototipo (MVP) di digital twin logistico con:

- Simulatore di convogli e depositi
- Raccolta di log e KPI
- Modello semplice di rischio
- Interfaccia utente minimale per lanciare simulazioni

> Nota: progetto personale sviluppato su Windows, con circa 2 ore di lavoro al giorno.
```

**Checklist**  
- [x] Esiste un `README.md` con titolo e descrizione breve del progetto

---

### Fine Giorno 3 – Verifica veloce

- [x] Struttura cartelle completata (`src`, `data`, `notebooks`, `docs`, `tests`)
- [x] File `__init__.py` creati
- [x] Progetto aperto in VS Code
- [x] `README.md` creato

Se tutto è ok, puoi passare al Giorno 4.

---

## Giorno 4 – Primo script Python di prova (simulatore “vuoto”)

### Obiettivo del giorno
Creare un **primo script Python eseguibile** per verificare che tutto funzioni (ambiente, struttura, VS Code).

Assicurati che l’ambiente `.venv` sia **attivo**.

---

### 1. Creare `src\sim\main_sim.py`

In VS Code:

1. Nella barra laterale, vai su `src` → `sim`
2. Clicca su **New File**
3. Chiamalo: `main_sim.py`
4. Inserisci questo contenuto:

```python
"""
Modulo principale del simulatore (versione di prova, Windows).

Per ora non fa nulla di complesso:
- stampa un messaggio di benvenuto
- dimostra che l'ambiente Python è configurato correttamente
"""


def main():
    print("=== Simulatore logistico – versione di prova (Windows) ===")
    print("L'ambiente Python è configurato correttamente.")
    print("Nei prossimi passi inizierai ad aggiungere logica di simulazione.")


if __name__ == "__main__":
    main()
```

Salva il file (`Ctrl + S`).

---

### 2. Eseguire lo script dal terminale (Windows)

Nel terminale, assicurati di essere nella cartella `digital-twin-logistico` e di avere l’ambiente `.venv` attivo.

1. Esegui il comando:

```bash
python -m src.sim.main_sim
```

oppure (se usi `py`):

```bash
py -m src.sim.main_sim
```

2. Dovresti vedere un output simile:

```text
=== Simulatore logistico – versione di prova (Windows) ===
L'ambiente Python è configurato correttamente.
Nei prossimi passi inizierai ad aggiungere logica di simulazione.
```

**Checklist**  
- [x] `src\sim\main_sim.py` esiste e contiene la funzione `main()`
- [x] `python -m src.sim.main_sim` (o `py -m src.sim.main_sim`) funziona e stampa il messaggio

---

### 3. (Opzionale) Eseguire lo script da VS Code

1. In VS Code, apri `src\sim\main_sim.py`
2. Controlla in basso a destra l’interprete Python selezionato:
   - clicca sulla versione di Python mostrata (es. “Python 3.10.11 ('.venv': venv)”)
   - assicurati di scegliere **l’interprete dentro `.venv`**
3. Premi il pulsante **Run** (triangolino in alto a destra nell’editor)
4. Verifica che venga aperto un terminale integrato e che compaia lo stesso output

**Checklist (opzionale)**  
- [x] So come eseguire lo script anche da VS Code

---

### Fine Giorno 4 – Verifica veloce

- [x] Posso eseguire `python -m src.sim.main_sim` senza errori
- [x] Vedo il messaggio di benvenuto nel terminale
- [x] (Opzionale) So eseguire lo script da VS Code

Se tutto è ok, sei pronto per aggiungere i primi test e salvare lo stato iniziale del progetto con Git nel Giorno 5.

---

## Giorno 5 – Test di base, script `run_checks.bat` e primo commit Git

### Obiettivo del giorno
- Aggiungere un **primo test automatico** con `pytest`
- Creare uno script `run_checks.bat` per lanciare i controlli base
- Fare il **primo commit Git** dello stato del progetto

Assicurati che l’ambiente `.venv` sia **attivo** prima di eseguire i comandi Python.

---

### 1. Verificare che `pytest` sia installato

Se hai già aggiunto `pytest` in `requirements.txt` (Giorno 2), dovrebbe essere installato.  
Se non sei sicuro:

1. Controlla il file `requirements.txt` e verifica che contenga la riga:
   ```txt
   pytest
   ```
2. Nel terminale (con `.venv` attivo), esegui di nuovo:
   ```bash
   pip install -r requirements.txt
   ```

**Checklist**  
- [x] `pytest` è presente in `requirements.txt`
- [x] `pip install -r requirements.txt` è stato eseguito senza errori gravi

---

### 2. Creare un test di esempio (`tests\test_dummy.py`)

1. In VS Code, nella cartella `tests`, crea il file `test_dummy.py`
2. Inserisci il seguente contenuto:

```python
def test_dummy():
    """
    Test di esempio per verificare che il framework di test funzioni.
    """
    assert 1 + 1 == 2
```

3. Salva il file.

4. Nel terminale (con `.venv` attivo), esegui:

```bash
pytest
```

5. Se tutto va bene, vedrai qualcosa come:

```text
============================= test session starts =============================
collected 1 item

tests/test_dummy.py .                                                    [100%]

============================== 1 passed in 0.XXs ==============================
```

**Checklist**  
- [x] Esiste `tests\test_dummy.py`
- [x] Il comando `pytest` gira e mostra `1 passed`

---

### 3. Creare lo script `run_checks.bat` (Windows)

Questo script servirà per lanciare velocemente i controlli base del progetto.

1. Nella cartella principale `digital-twin-logistico`, crea un file chiamato `run_checks.bat`
2. Inserisci il seguente contenuto:

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
echo Eseguo lo script di prova del simulatore...
echo ==============================

python -m src.sim.main_sim

echo.
echo ==============================
echo Controlli completati.
echo Premi un tasto per chiudere.
echo ==============================
pause
```

3. Salva il file.

4. Per provarlo:
   - fai doppio clic su `run_checks.bat` in Esplora File **oppure**
   - esegui nel terminale (anche senza ambiente attivo):
     ```bash
     run_checks.bat
     ```

5. Dovresti vedere:
   - attivazione dell’ambiente virtuale
   - esecuzione dei test `pytest`
   - esecuzione dello script `main_sim`

**Checklist**  
- [x] Esiste `run_checks.bat`
- [x] Lanciando `run_checks.bat` vengono eseguiti i test e lo script di prova

---

### 4. Fare il primo commit Git

Ora salvi lo stato iniziale del progetto nel repository Git locale.

1. Nel terminale (dentro `digital-twin-logistico`), controlla lo stato:

```bash
git status
```

2. Aggiungi tutti i file alla “staging area”:

```bash
git add .
```

3. Crea il primo commit con un messaggio chiaro:

```bash
git commit -m "Setup iniziale progetto: ambiente Windows, struttura base, primo script e test dummy"
```

4. Verifica lo stato:

```bash
git status
```

Dovresti vedere qualcosa come:
- `nothing to commit, working tree clean`

**Checklist**  
- [ ] Ho eseguito `git add .`
- [ ] Ho eseguito `git commit -m "..."` senza errori
- [ ] `git status` mostra “working tree clean”

---

## Fine Fase 01 – Checklist finale

Quando tutte (o quasi tutte) le caselle seguenti sono spuntate, la **Fase 01 è completata**.

- [ ] `py --version` o `python --version` funziona su Windows
- [ ] `git --version` funziona
- [ ] VS Code è installato e apre la cartella `digital-twin-logistico`
- [ ] Esiste la cartella del progetto: `C:\Users\TUO_UTENTE\Progetti\digital-twin-logistico`
- [ ] Il repository Git è inizializzato (`git init` eseguito)
- [ ] Esiste un file `.gitignore` con almeno `.venv/` e `__pycache__/`
- [ ] Esiste un ambiente virtuale `.venv` e so attivarlo
- [ ] I pacchetti di `requirements.txt` sono installati
- [ ] Esistono le cartelle: `src`, `data`, `notebooks`, `docs`, `tests`
- [ ] Esiste `src\sim\main_sim.py` e posso eseguirlo con `python -m src.sim.main_sim`
- [ ] Posso lanciare i test con `pytest` (e il test dummy passa)
- [ ] Posso lanciare `run_checks.bat` e vedere tutto funzionare
- [ ] Ho fatto il primo commit Git con lo stato iniziale del progetto

A questo punto sei pronto per passare alla **Fase 02**, dove inizierai a costruire il **simulatore vero e proprio**.
