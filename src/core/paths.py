# src/core/paths.py
from pathlib import Path
import sys

def get_base_dir() -> Path:
    """
    Retorna a pasta base do app, tanto em dev quanto dentro do EXE.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # rodando empacotado (PyInstaller)
        return Path(sys._MEIPASS)
    # rodando em dev
    return Path(__file__).resolve().parents[2]
