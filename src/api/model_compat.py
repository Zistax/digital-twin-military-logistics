"""Resolve historical pickle module names without changing frozen artifacts."""

import importlib
from pathlib import Path
import sys

import joblib


def load_legacy_artifact(path):
    for suffix in ("", ".initial_prediction", ".rolling_prediction"):
        module = importlib.import_module("src.logistics" + suffix)
        name = "logistics" + suffix
        previous = sys.modules.get(name)
        if (
            previous is not None
            and Path(previous.__file__).resolve() != Path(module.__file__).resolve()
        ):
            raise ValueError("conflicting historical model module: " + name)
        sys.modules.setdefault(name, module)
    return joblib.load(path)
