from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass
class Settings:
    """
    Configurações centrais do bot.

    Obs:
    - Existe apenas UM CSV ativo por vez (csv_ativo_path).
    - O histórico de inserções será armazenado em arquivos de log (pasta_logs).
    """

    # arquivo de config no disco (data/config.json)
    CONFIG_FILE: ClassVar[Path]

    csv_ativo_path: Path
    pasta_logs: Path
    pasta_imagens: Path
    chrome_profile_path: Path | str
    descricao_padrao: str

    # --------------- defaults / fábrica ---------------

    @classmethod
    def _base_dirs(cls) -> tuple[Path, Path]:
        """
        Retorna (BASE_DIR, DATA_DIR).

        Considerando estrutura tipo:
        projeto/
          data/
          src/
            core/
              settings.py  (este arquivo)
        """
        base_dir = Path(__file__).resolve().parents[2]
        data_dir = base_dir / "data"
        return base_dir, data_dir

    @classmethod
    def defaults(cls) -> "Settings":
        """
        Cria uma instância de Settings com valores padrão.
        """
        base_dir, data_dir = cls._base_dirs()

        csv_ativo = data_dir / "items.csv"
        pasta_logs = data_dir / "logs"
        pasta_imagens = data_dir / "img"

        # valor default genérico; o usuário pode sobrescrever no config.json
        chrome_profile = base_dir / "chrome-profile"

        descricao_padrao = (
            """Item Delivery Instructions

            1. After payment, the seller will send a private server link via chat.
            2. Buyer must provide their in-game username for verification.
            3. Join the private server using the link provided.
            4. Locate and steal the Brainrot pet that matches your purchase.
            5. Bring the Brainrot back to your base.
            6. Once the pet is secured in your base, the transaction is considered successful.
            -- Don't be a dumb trying to scam me. I record all times.

            Fast – Easy – Secure

            Thank you for your purchase!

            Ignore;
            Tags:
            RAINBOW-GOLD-DIAMOND-BLOODROOT-GALAXY-BLOODROT-Secret-La Grande-Garama-Los Combinasionas-Chicleteira Bicicleteira-Graipuss Medussi-La Vacca-Tralalero Tralala-Los-Rainbow-Dragon-Pot Hotspot-Nuclearo-Ban Hammer-HD Admin-Matteo-Esok-Ketupat-Noo my hotspotsitos-Sphagetti-Spag-toualetti-Sphageti-Burguro-Fryuro-Yin yang-dragon caneloni-Strawberry Elephant-Los 67
            """
        )

        return cls(
            csv_ativo_path=csv_ativo,
            pasta_logs=pasta_logs,
            pasta_imagens=pasta_imagens,
            chrome_profile_path=chrome_profile,
            descricao_padrao=descricao_padrao,
        )

    # --------------- persistência (config.json) ---------------

    @classmethod
    def load(cls) -> "Settings":
        """
        Carrega configurações de data/config.json.

        - Se o arquivo não existir ou estiver inválido, retorna defaults().
        - Se algum campo estiver ausente, cai no valor default daquele campo.
        """
        # inicializa CONFIG_FILE se ainda não tiver sido setado
        if not hasattr(cls, "CONFIG_FILE"):
            _, data_dir = cls._base_dirs()
            cls.CONFIG_FILE = data_dir / "config.json"

        config_file = cls.CONFIG_FILE

        # Se não existe, retorna defaults
        if not config_file.exists():
            return cls.defaults()

        try:
            with config_file.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError):
            # Qualquer problema de leitura/parse -> volta para defaults
            return cls.defaults()

        defaults = cls.defaults()

        def _path_or_default(key: str, default_path: Path) -> Path:
            value = raw.get(key)
            return Path(value) if isinstance(value, str) and value.strip() else default_path

        csv_ativo_path = _path_or_default("csv_ativo_path", defaults.csv_ativo_path)
        pasta_logs = _path_or_default("pasta_logs", defaults.pasta_logs)
        pasta_imagens = _path_or_default("pasta_imagens", defaults.pasta_imagens)

        chrome_raw = raw.get("chrome_profile_path")
        chrome_profile_path: Path | str
        if isinstance(chrome_raw, str) and chrome_raw.strip():
            # aqui deixo como string; se quiser, pode envolver em Path
            chrome_profile_path = chrome_raw
        else:
            chrome_profile_path = defaults.chrome_profile_path

        descricao_padrao = raw.get("descricao_padrao") or defaults.descricao_padrao

        return cls(
            csv_ativo_path=csv_ativo_path,
            pasta_logs=pasta_logs,
            pasta_imagens=pasta_imagens,
            chrome_profile_path=chrome_profile_path,
            descricao_padrao=descricao_padrao,
        )

    def save(self) -> None:
        """
        Salva as configurações atuais em data/config.json.

        - Cria a pasta data/ se ainda não existir.
        - Usa UTF-8, com indentação legível.
        """
        if not hasattr(self.__class__, "CONFIG_FILE"):
            _, data_dir = self.__class__._base_dirs()
            self.__class__.CONFIG_FILE = data_dir / "config.json"

        config_file = self.__class__.CONFIG_FILE
        config_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "csv_ativo_path": str(self.csv_ativo_path),
            "pasta_logs": str(self.pasta_logs),
            "pasta_imagens": str(self.pasta_imagens),
            "chrome_profile_path": str(self.chrome_profile_path),
            "descricao_padrao": self.descricao_padrao,
        }

        with config_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
