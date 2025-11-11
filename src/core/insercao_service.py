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
    """
    caminho = _to_path(caminho_csv)

    if not caminho.exists():
        return []

    itens: List[ItemInsercao] = []

    with caminho.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not any(row.values()):
                continue
            itens.append(ItemInsercao.from_csv_row(row))

    return itens


def salvar_insercao(caminho_csv: PathLike, itens: Iterable[ItemInsercao]) -> None:
    """
    Sobrescreve o CSV informado com os itens fornecidos.

    - Garante que a pasta exista.
    - Sempre escreve o cabeçalho.
    """
    caminho = _to_path(caminho_csv)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    with caminho.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ItemInsercao.CSV_COLUMNS)
        writer.writeheader()
        for item in itens:
            writer.writerow(item.to_csv_row())


# -------------------------------------------------------------------
# 3) Adicionar ou incrementar item (por nome) em qualquer CSV
# -------------------------------------------------------------------
def adicionar_ou_incrementar_item(
    caminho_csv: PathLike, novo_item: ItemInsercao
) -> ItemInsercao:
    """
    Adds a new item to the insertion OR increments the quantity if an item
    with the same identity_key() (currently: same TITLE, case-insensitive) already exists.

    Flow:
    - Loads existing items from the CSV;
    - Compares identity_key() (defined in ItemInsercao);
    - If a match is found → increments its quantity;
    - Otherwise → appends the new item;
    - Saves everything back to the CSV;
    - Returns the resulting (possibly merged) item.
    """
    caminho = _to_path(caminho_csv)
    itens = carregar_insercao(caminho)

    novo_key = novo_item.identity_key()
    item_encontrado: ItemInsercao | None = None

    # look for an existing item with the same title (via identity_key)
    for item in itens:
        if item.identity_key() == novo_key:
            item_encontrado = item
            break

    if item_encontrado:
        item_encontrado.quantidade += novo_item.quantidade
        item_resultante = item_encontrado
    else:
        itens.append(novo_item)
        item_resultante = novo_item

    salvar_insercao(caminho, itens)
    return item_resultante
