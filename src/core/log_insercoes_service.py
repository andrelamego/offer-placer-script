# core/log_insercoes_service.py
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Union

from src.core.settings import Settings


PathLike = Union[str, Path]


def _to_path(p: PathLike) -> Path:
    return p if isinstance(p, Path) else Path(p)


def registrar_log_insercao(caminho_csv_insercao: PathLike) -> Path:
    """
    Cria um "snapshot" em CSV da inserção informada, com uma coluna extra
    de timestamp, e salva em data/logs/.

    - Lê o CSV de inserção (nome, titulo, imgUrl, descricao, quantidade, preco);
    - Gera um novo CSV com as mesmas colunas + data_hora_insercao;
    - Salva em settings.pasta_logs com nome baseado na data/hora atual:
      ex.: insercao_20251106_153045_log.csv
    - Retorna o Path do arquivo de log criado.
    """
    caminho_insercao = _to_path(caminho_csv_insercao)

    if not caminho_insercao.exists():
        raise FileNotFoundError(f"CSV da inserção não encontrado: {caminho_insercao}")

    # carrega settings para pegar a pasta de logs
    settings = Settings.load()
    pasta_logs: Path = settings.pasta_logs
    pasta_logs.mkdir(parents=True, exist_ok=True)

    # timestamp para nome do arquivo e para a coluna
    ts_nome = datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_coluna = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # nome simples baseado em data/hora (poderíamos incluir o stem se quiser)
    log_path = pasta_logs / f"insercao_{ts_nome}_log.csv"

    with caminho_insercao.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        fieldnames_orig = reader.fieldnames or []

        # adiciona coluna extra ao final
        fieldnames_log = list(fieldnames_orig) + ["data_hora_insercao"]

        with log_path.open("w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames_log)
            writer.writeheader()

            for row in reader:
                if not any(row.values()):
                    continue  # ignora linhas completamente vazias

                row_log = dict(row)
                row_log["data_hora_insercao"] = ts_coluna
                writer.writerow(row_log)

    return log_path
