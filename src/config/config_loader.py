from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import os
import yaml

# Cartella base delle configurazioni
BASE_CONF_DIR = Path("conf")


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    """Carica un file YAML e restituisce un dizionario.

    Se il file non esiste, lancia FileNotFoundError.
    """
    if not path.exists():
        raise FileNotFoundError(f"File di configurazione non trovato: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError(
            f"Il file di configurazione {path} non contiene un dict YAML valido."
        )

    return data


def load_sim_config(env: str | None = None) -> Dict[str, Any]:
    """Carica la configurazione della simulazione.

    - env: nome dell'ambiente (default, dev, prod...). Se None, usa la variabile
      d'ambiente SIM_ENV, altrimenti 'default'.

    Ritorna un dict con le chiavi sotto la sezione 'sim'.
    """
    if env is None:
        env = os.environ.get("SIM_ENV", "default")

    path = BASE_CONF_DIR / "sim" / f"{env}.yml"
    raw = _load_yaml_file(path)
    sim_conf = raw.get("sim", raw)
    if not isinstance(sim_conf, dict):
        raise ValueError("sim section must be a dictionary")
    return sim_conf


def load_ml_config(env: str | None = None) -> Dict[str, Any]:
    """Carica la configurazione della parte ML.

    - env: nome dell'ambiente (default, dev, prod...). Se None, usa la variabile
      d'ambiente ML_ENV, altrimenti 'default'.

    Ritorna un dict con le chiavi sotto la sezione 'ml'.
    """
    if env is None:
        env = os.environ.get("ML_ENV", "default")

    path = BASE_CONF_DIR / "ml" / f"{env}.yml"
    raw = _load_yaml_file(path)
    ml_conf = raw.get("ml", raw)
    if not isinstance(ml_conf, dict):
        raise ValueError("ml section must be a dictionary")
    return ml_conf
