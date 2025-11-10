# Eldorado Offer Placer
# Copyright (c) 2025 André Lamego
# Licensed under Dual License (MIT + Proprietary)
# For commercial use, contact: andreolamego@gmail.com

from __future__ import annotations
import subprocess
import datetime
from pathlib import Path

# Fallback local
__fallback_version__ = "0.3.1-alpha"


def get_version() -> str:
    """Retorna a versão do app, preferindo tag do Git, com fallback local."""
    version = __fallback_version__
    try:
        # tenta pegar o nome da última tag git
        version = (
            subprocess.check_output(["git", "describe", "--tags"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        pass

    # Adiciona data do build (útil para identificar builds rápidos)
    build_date = datetime.datetime.now().strftime("%Y-%m-%d")
    return f"{version} ({build_date})"


def short_version() -> str:
    """Versão curta sem data, ex.: v0.3.0"""
    try:
        version = (
            subprocess.check_output(["git", "describe", "--tags"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
        return version
    except Exception:
        return __fallback_version__
