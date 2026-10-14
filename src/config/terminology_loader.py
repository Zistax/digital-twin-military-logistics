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
        data = yaml.safe_load(f)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("terminology configuration must be a dictionary")

    term_map = data.get("terminology", {})
    if not isinstance(term_map, dict):
        raise ValueError(f"Sezione 'terminology' non valida in {path}")

    # Convertiamo le chiavi in stringhe lower-case, per sicurezza
    normalized = {str(k).lower(): str(v) for k, v in term_map.items()}
    return normalized


def translate_term(term: str, mapping: Dict[str, str]) -> str:
    """Traduce un termine canonico usando il mapping; se non trovato, restituisce
    l'originale."""
    return mapping.get(term.lower(), term)
