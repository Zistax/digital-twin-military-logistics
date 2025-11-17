# conftest.py nella root del progetto
import os
import sys

# Root del progetto (cartella dove sta questo file)
ROOT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(ROOT_DIR, "src")

# Aggiungiamo la cartella "src" al sys.path, così il package "sim" è importabile
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# (Opzionale) debug, puoi commentare queste tre righe se non ti servono
print("[conftest] ROOT_DIR =", ROOT_DIR)
print("[conftest] SRC_DIR  =", SRC_DIR)
print("[conftest] sys.path[0:3] =", sys.path[0:3])
