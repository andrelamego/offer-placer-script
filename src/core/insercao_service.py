# Eldorado Offer Placer
# Copyright (c) 2025 André Lamego
# Licensed under Dual License (MIT + Proprietary)
# For commercial use, contact: andreolamego@gmail.com

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List, Union

from src.core.models import ItemInsercao
from src.core.settings import Settings

PathLike = Union[str, Path]


def _to_path(p: PathLike) -> Path:
    return p if isinstance(p, Path) else Path(p)


# -------------------------------------------------------------------
# 1) Nova inserção (CSV ativo único)
# -------------------------------------------------------------------
def nova_insercao(settings: Settings) -> Path:
    """
    Reseta o CSV ativo definido em settings.csv_ativo_path.

    Comportamento:
    - Garante que a pasta do CSV exista;
    - Apaga qualquer conteúdo anterior;
    - Escreve apenas o cabeçalho padrão:
      nome, titulo, imgUrl, descricao, quantidade, preco
    - Retorna o Path do CSV ativo.
    """
    caminho = settings.csv_ativo_path
    caminho = _to_path(caminho)

    # garante que a pasta existe
    caminho.parent.mkdir(parents=True, exist_ok=True)

    # recria o arquivo do zero com apenas o cabeçalho
    with caminho.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ItemInsercao.CSV_COLUMNS)
        writer.writeheader()

    return caminho


# -------------------------------------------------------------------
# 2) Carregar / salvar inserção (trabalham em QUALQUER CSV)
#    – para o CSV ativo, basta passar settings.csv_ativo_path.
# -------------------------------------------------------------------
def carregar_insercao(caminho_csv: PathLike) -> List[ItemInsercao]:
    """
    Lê um CSV de inserção e retorna uma lista de ItemInsercao.

    - Se o arquivo não existir, retorna lista vazia.
    - Ignora linhas completamente vazias.
    - Se a coluna 'descricao' for 'DEFAULT', substitui pela
      descrição padrão das Settings e marca descricao_is_default=True
      (quando o atributo existir no ItemInsercao).
    """
    caminho = _to_path(caminho_csv)

    if not caminho.exists():
        return []

    # Carrega settings para obter a descrição padrão
    settings = Settings.load()

    itens: List[ItemInsercao] = []

    with caminho.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not any(row.values()):
                continue

            # Cria o item a partir da linha (comportamento antigo)
            item = ItemInsercao.from_csv_row(row)

            # Trata o campo descricao = "DEFAULT"
            raw_desc = (row.get("descricao") or "").strip()
            if raw_desc == "DEFAULT":
                # substitui pela descrição padrão das settings
                item.descricao = settings.descricao_padrao
                # se o dataclass tiver esse campo, marcamos como default
                if hasattr(item, "descricao_is_default"):
                    setattr(item, "descricao_is_default", True)
            else:
                # não é DEFAULT → garante flag False se campo existir
                if hasattr(item, "descricao_is_default"):
                    setattr(item, "descricao_is_default", False)

            itens.append(item)

    return itens


def salvar_insercao(caminho_csv: PathLike, itens: Iterable[ItemInsercao]) -> None:
    """
    Sobrescreve o CSV informado com os itens fornecidos.

    - Garante que a pasta exista.
    - Sempre escreve o cabeçalho.
    - Se item.descricao_is_default == True, grava "DEFAULT" na coluna
      'descricao' em vez do texto completo.
    """
    caminho = _to_path(caminho_csv)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    with caminho.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ItemInsercao.CSV_COLUMNS)
        writer.writeheader()

        for item in itens:
            # Usa a linha padrão gerada pelo model
            row = item.to_csv_row()

            # Se o ItemInsercao tiver a flag descricao_is_default, usamos
            # "DEFAULT" no CSV quando for True.
            desc_is_default = False
            if hasattr(item, "descricao_is_default"):
                try:
                    desc_is_default = bool(getattr(item, "descricao_is_default"))
                except Exception:
                    desc_is_default = False

            if desc_is_default:
                row["descricao"] = "DEFAULT"

            writer.writerow(row)


# -------------------------------------------------------------------
# 3) Adicionar ou incrementar item (por identity_key) em qualquer CSV
# -------------------------------------------------------------------
def adicionar_ou_incrementar_item(
    caminho_csv: PathLike, novo_item: ItemInsercao
) -> ItemInsercao:
    """
    Adds a new item to the insertion OR increments the quantity if an item
    with the same identity_key() already exists.

    identity_key() é definido em ItemInsercao e atualmente compara
    pelo TÍTULO (case-insensitive), garantindo que o mesmo brainrot
    com a mesma geração/variação não crie linhas duplicadas.

    Fluxo:
    - Carrega itens existentes do CSV;
    - Compara identity_key() de cada item com o novo_item;
    - Se encontrar um existente → incrementa quantidade;
    - Caso contrário → adiciona novo_item;
    - Salva tudo de volta no CSV;
    - Retorna o item resultante (que pode ser o existente incrementado
      ou o novo item).
    """
    caminho = _to_path(caminho_csv)
    itens = carregar_insercao(caminho)

    novo_key = novo_item.identity_key()
    item_encontrado: ItemInsercao | None = None

    for item in itens:
        if item.identity_key() == novo_key:
            item_encontrado = item
            break

    if item_encontrado is not None:
        item_encontrado.quantidade += novo_item.quantidade
        item_resultante = item_encontrado
    else:
        itens.append(novo_item)
        item_resultante = novo_item

    salvar_insercao(caminho, itens)
    return item_resultante
