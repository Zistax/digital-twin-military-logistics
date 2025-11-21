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

- Il core del progetto (simulatore, modello di rischio, API, UI di base) e' pensato per
  una licenza open source (es. Apache-2.0).
- Il file `LICENSE` alla radice del repository definisce la licenza del core.
- La cartella `plugins/` e' prevista per componenti opzionali che possono avere
  licenze diverse (es. plugin proprietari, connettori specifici per sistemi esterni).