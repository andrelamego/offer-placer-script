# Eldorado Offer Placer
# Copyright (c) 2025 André Lamego
# Licensed under Dual License (MIT + Proprietary)
# For commercial use, contact: andreolamego@gmail.com

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# BASE_DIR = raiz do projeto (ajusta se seu layout for diferente)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_PATH = DATA_DIR / "config.json"


@dataclass
class Settings:
    csv_ativo_path: Path
    pasta_logs: Path
    pasta_imagens: Path
    chrome_profile_path: Optional[Path]
    descricao_padrao: str
    initial_setup_done: bool = False

    # ----------------------------------------------------
    # Defaults
    # ----------------------------------------------------
    @classmethod
    def defaults(cls) -> "Settings":
        data_dir = DATA_DIR
        logs_dir = data_dir / "logs"
        imagens_dir = data_dir / "img"

        return cls(
            csv_ativo_path=data_dir / "itens.csv",
            pasta_logs=logs_dir,
            pasta_imagens=imagens_dir,
            chrome_profile_path=None,
            descricao_padrao=(
                "Default description here.\n"
                "You can edit this in the Configs screen."
            ),
            initial_setup_done=False,
        )

    # ----------------------------------------------------
    # Load / Save
    # ----------------------------------------------------
    @classmethod
    def load(cls) -> "Settings":
        """
        Load settings from data/config.json.
        If missing or invalid, returns defaults and saves them.
        """
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        if not CONFIG_PATH.exists():
            settings = cls.defaults()
            settings.save()
            return settings

        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            settings = cls.defaults()
            settings.save()
            return settings

        defaults = cls.defaults()

        # csv_ativo_path
        csv_raw = raw.get("csv_ativo_path")
        csv_ativo_path = Path(csv_raw) if csv_raw else defaults.csv_ativo_path

        # pasta_logs
        logs_raw = raw.get("pasta_logs")
        pasta_logs = Path(logs_raw) if logs_raw else defaults.pasta_logs

        # pasta_imagens
        imgs_raw = raw.get("pasta_imagens")
        pasta_imagens = Path(imgs_raw) if imgs_raw else defaults.pasta_imagens

        # chrome_profile_path
        chrome_raw = raw.get("chrome_profile_path")
        chrome_profile_path = Path(chrome_raw) if chrome_raw else None

        descricao_padrao = raw.get("descricao_padrao", defaults.descricao_padrao)
        initial_setup_done = bool(raw.get("initial_setup_done", False))

        return cls(
            csv_ativo_path=csv_ativo_path,
            pasta_logs=pasta_logs,
            pasta_imagens=pasta_imagens,
            chrome_profile_path=chrome_profile_path,
            descricao_padrao=descricao_padrao,
            initial_setup_done=initial_setup_done,
        )

    def save(self) -> None:
        """
        Save settings to data/config.json (UTF-8).
        All Path fields are converted to strings.
        """
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        data = {
            "csv_ativo_path": str(self.csv_ativo_path) if self.csv_ativo_path else None,
            "pasta_logs": str(self.pasta_logs) if self.pasta_logs else None,
            "pasta_imagens": str(self.pasta_imagens) if self.pasta_imagens else None,
            "chrome_profile_path": (
                str(self.chrome_profile_path) if self.chrome_profile_path else None
            ),
            "descricao_padrao": self.descricao_padrao,
            "initial_setup_done": bool(self.initial_setup_done),
        }

        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def ensure_dirs(self) -> None:
        """Create main folders if needed."""
        self.csv_ativo_path.parent.mkdir(parents=True, exist_ok=True)
        self.pasta_logs.mkdir(parents=True, exist_ok=True)
        self.pasta_imagens.mkdir(parents=True, exist_ok=True)