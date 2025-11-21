# Fase 24 – DevOps & Qualità locale (Parte 1, Giorni 1–3, Windows)

> **Obiettivo pratico (Parte 1)**  
> Mettere in piedi una base di **DevOps & qualità** locale per il progetto:
>
> - formattazione automatica del codice (**black**),
> - linting veloce (**ruff**),
> - misurazione di **coverage** dei test,
> - controllo dei **tipi** con `mypy`,
> - il tutto agganciato a **pre-commit** per evitare errori nei commit.

L’obiettivo è avere comandi semplici che puoi lanciare prima di ogni commit
e una base per una futura CI (che vedremo nella Parte 2).


---

## Struttura Fase 24 – Parte 1

- **Giorno 1** – Setup `requirements-dev` + `pre-commit` (black + ruff)
- **Giorno 2** – Coverage dei test con `pytest-cov`
- **Giorno 3** – Controllo tipi con `mypy`


---

## Giorno 1 – Setup pre-commit (black + ruff)

### Obiettivo del giorno
- Separare le dipendenze “di sviluppo” in un file dedicato,
- configurare `pre-commit` con **black** e **ruff**,
- eseguire una prima passata di formattazione / linting.


---

### 1. Creare `requirements-dev.txt`

1. Nella **root del progetto** (dove hai `requirements.txt`), crea il file:

   - `requirements-dev.txt`

2. Inserisci questo contenuto base:

```txt
pre-commit
black
ruff
mypy
pytest-cov
```

> Alcune di queste librerie potrebbero essere già nel tuo `requirements.txt`.
> Non è un problema se sono duplicate; `pip` le gestisce senza errori.

3. Installa le dipendenze di sviluppo (da PowerShell/cmd, root progetto, `.venv` attivo):

```bash
pip install -r requirements-dev.txt
```

**Checklist**
- [ ] Esiste `requirements-dev.txt`
- [ ] `pip install -r requirements-dev.txt` gira senza errori


---

### 2. Creare il file `.pre-commit-config.yaml`

1. Nella root del progetto, crea il file:

   - `.pre-commit-config.yaml`

2. Inserisci una configurazione semplice per black + ruff:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: ["--fix"]
```

> Le versioni (`rev`) possono essere aggiornate in futuro.  
> Per ora vanno bene così, l’importante è avere una versione stabile.

3. Salva il file.

**Checklist**
- [ ] Esiste `.pre-commit-config.yaml` con black + ruff configurati


---

### 3. Inizializzare pre-commit

1. Sempre nella root del progetto (con `.venv` attivo):

```bash
pre-commit install
```

Questo comando:

- crea gli hook di pre-commit nella tua repo git,
- fa sì che ad ogni `git commit` vengano eseguiti automaticamente black + ruff
  sui file modificati.

2. Esegui una prima passata su **tutti** i file:

```bash
pre-commit run --all-files
```

- Potrebbe essere un po’ lenta la prima volta (scarica i repo degli hook).
- Se black/ruff fanno modifiche, vedrai messaggi del tipo “reformatted … / fixed …”.

3. Quando finisce, verifica se ci sono errori non sistemati automaticamente.
   In quel caso dovrai correggerli a mano (es. import inutilizzati, variabili non usate).

**Checklist (fine Giorno 1)**
- [ ] `pre-commit install` eseguito
- [ ] `pre-commit run --all-files` gira senza errori finali
- [ ] Il codice è formattato da black e ripulito da ruff


---

## Giorno 2 – Coverage dei test con `pytest-cov`

### Obiettivo del giorno
- Misurare la **coverage** dei test,
- avere un comando semplice per vedere quali file non sono ancora coperti.


---

### 1. Creare (o aggiornare) `pytest.ini`

1. Nella root del progetto, verifica se esiste già un file `pytest.ini`.
   - Se esiste, **non cancellarlo**: lo modifichi.
   - Se non esiste, crealo.

2. Fai in modo che contenga almeno:

```ini
[pytest]
testpaths = tests
```

> Se ci sono già altre opzioni (`addopts`, ecc.), lasciale; aggiungi solo
> `testpaths = tests` se manca.

3. Salva il file.

**Checklist**
- [ ] `pytest.ini` presente con `testpaths = tests`


---

### 2. Eseguire i test con coverage

1. Dal terminale, root progetto, `.venv` attivo:

```bash
pytest --cov=src --cov-report=term-missing
```

- `--cov=src` dice a pytest-cov di misurare la coverage sul codice in `src/`,
- `--cov-report=term-missing` mostra anche le righe non coperte.

2. Alla fine vedrai una tabella simile a:

```text
Name                                  Stmts   Miss  Cover   Missing
-------------------------------------------------------------------
src/ml/train_risk_model.py             120     30    75%    10-20, 80-90
src/api/app.py                          90     40    55%    45-60, 70-80
...
-------------------------------------------------------------------
TOTAL                                  500    150    70%
```

3. Prenditi nota del valore `TOTAL` (es. 60–70%).  
   Un obiettivo realistico iniziale potrebbe essere **≥60%**, da aumentare con calma.

**Checklist**
- [ ] `pytest --cov=src --cov-report=term-missing` gira senza errori
- [ ] Hai un valore di coverage totale da cui partire


---

### 3. (Opzionale) Aggiungere un comando comodo nel README

Puoi già annotare nel README una sezione tipo:

```markdown
Per eseguire i test con coverage:

```bash
pytest --cov=src --cov-report=term-missing
```
```

Lo rifiniremo meglio nella Parte 2 di questa fase.

**Checklist (fine Giorno 2)**
- [ ] Sai come lanciare pytest con coverage
- [ ] Hai un’idea di quali file sono poco o per nulla coperti dai test


---

## Giorno 3 – Controllo tipi con `mypy`

### Obiettivo del giorno
- Abilitare un controllo di tipi statico con `mypy`,
- configurarlo in modo non troppo “punitivo” per iniziare,
- avere un comando unico `mypy src`.


---

### 1. Creare `mypy.ini`

1. Nella root del progetto, crea il file:

   - `mypy.ini`

2. Inserisci questa configurazione base:

```ini
[mypy]
python_version = 3.11
warn_return_any = False
warn_unused_configs = True

# Semplifica l'uso iniziale di mypy:
ignore_missing_imports = True

# Cartelle da controllare (puoi restringere se vuoi):
mypy_path = src
```

> Puoi adattare `python_version` alla versione che stai usando (es. 3.10).

3. Salva il file.

**Checklist**
- [ ] Esiste `mypy.ini` con configurazione base


---

### 2. Prima esecuzione di `mypy`

1. Dal terminale, root progetto, `.venv` attivo:

```bash
mypy src
```

2. Possibilità:

- **Nessun output / “Success: no issues found in X source files”**  
  → ottimo, significa che mypy non ha trovato problemi gravi con la config attuale.

- **Appaiono errori** (es. “Incompatible types”, “Missing return statement”):
  - leggili uno alla volta,
  - risolvi i casi più chiari (es. aggiungi annotazioni di tipo mancante),
  - se ci sono punti troppo complessi, puoi per ora “escludere” un singolo file
    aggiungendo in `mypy.ini` una sezione tipo:

    ```ini
    [mypy-src.api.app]
    ignore_errors = True
    ```

    (meglio non abusarne, ma è utile per iniziare).

3. Dopo qualche fix, rilancia `mypy src` fino a quando la situazione è sotto controllo
   (non serve arrivare a zero errori subito).

**Checklist**
- [ ] `mypy src` gira senza crash
- [ ] Hai un’idea dei punti più “fragili” dal punto di vista dei tipi


---

### 3. Collegare mentalmente i tre strumenti

A questo punto hai:

- **pre-commit** con **black + ruff**: ti aiutano a mantenere il codice pulito,
- **pytest + pytest-cov**: ti danno una misura di quanta logica è coperta dai test,
- **mypy**: ti aiuta a scovare problemi di tipo prima che finiscano in runtime.

Nella **Parte 2** di questa fase collegherai tutto in:

- uno script `tasks.bat` con comandi `test`, `lint`, `typecheck`, `quality`,
- una pipeline CI (GitHub Actions) che esegue gli stessi controlli in automatico,
- una sezione `DevOps & Qualità` nel README.

**Checklist (fine Giorno 3 – fine Parte 1)**
- [ ] `requirements-dev.txt` creato e usato
- [ ] `pre-commit` attivo con black + ruff
- [ ] `pytest --cov` funzionante
- [ ] `mypy src` eseguibile e ragionevolmente sotto controllo
