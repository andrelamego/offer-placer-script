# Eldorado Offer Placer
# Copyright (c) 2025 André Lamego
# Licensed under Dual License (MIT + Proprietary)
# For commercial use, contact: andreolamego@gmail.com

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar, Dict


@dataclass
class ItemInsercao:
    """
    Representa uma linha do CSV de uma inserção.

    Colunas:
    nome, titulo, imgUrl, descricao, quantidade, preco
    """

    CSV_COLUMNS: ClassVar[list[str]] = [
        "nome",
        "titulo",
        "imgUrl",
        "descricao",
        "quantidade",
        "preco",
    ]

    nome: str
    titulo: str
    imgUrl: str
    descricao: str
    quantidade: int = 1
    preco: Decimal = Decimal("0.00")
    # flag interna para saber se essa descrição é a padrão das Settings
    descricao_is_default: bool = False

    # --------- helpers de CSV ---------

    @classmethod
    def from_csv_row(cls, row: Dict[str, Any]) -> "ItemInsercao":
        """
        Converte um dict (linha de csv.DictReader) em ItemInsercao.
        Faz conversão de quantidade e preco.

        OBS:
        - Aqui NÃO tratamos "DEFAULT" -> descrição padrão,
          isso é feito em inserircao_service.carregar_insercao,
          pois lá temos acesso às Settings.
        """
        nome = (row.get("nome") or "").strip()
        titulo = (row.get("titulo") or "").strip()
        imgUrl = (row.get("imgUrl") or "").strip()
        descricao = (row.get("descricao") or "").strip()

        quantidade_raw = (row.get("quantidade") or "").strip()
        preco_raw = (row.get("preco") or "").strip()

        # quantidade -> int (default 0 se vier vazio/errado)
        try:
            quantidade = int(quantidade_raw) if quantidade_raw else 0
        except ValueError:
            quantidade = 0

        # preco -> Decimal (default 0 se vier vazio/errado)
        try:
            preco = (
                Decimal(preco_raw.replace(",", "."))
                if preco_raw
                else Decimal("0.00")
            )
        except (InvalidOperation, AttributeError):
            preco = Decimal("0.00")

        return cls(
            nome=nome,
            titulo=titulo,
            imgUrl=imgUrl,
            descricao=descricao,
            quantidade=quantidade,
            preco=preco,
            # ao carregar do CSV não sabemos ainda se é default,
            # isso será ajustado em inserircao_service.carregar_insercao
            descricao_is_default=False,
        )

    def to_csv_row(self) -> Dict[str, str]:
        """
        Converte o ItemInsercao em um dict pronto para csv.DictWriter.
        Todos os valores são strings.

        Se descricao_is_default == True, grava "DEFAULT" no campo descricao
        (a descrição real fica nas Settings).
        """
        descricao_csv = "DEFAULT" if self.descricao_is_default else self.descricao

        return {
            "nome": self.nome,
            "titulo": self.titulo,
            "imgUrl": self.imgUrl,
            "descricao": descricao_csv,
            "quantidade": str(self.quantidade),
            "preco": f"{self.preco:.2f}",  # 2 casas decimais
        }

    # --------- critério de "mesmo item" dentro da inserção ---------

    def identity_key(self) -> tuple[str]:
        """
        Define quando dois itens pertencem ao mesmo brainrot
        dentro de UMA inserção.

        Critério atual:
        - mesmo nome (case-insensitive)
        - mesmo título (case-insensitive)

        Isso garante que o mesmo brainrot com a mesma geração/variação
        não crie linhas duplicadas, apenas incrementa a quantidade.
        """
        return (self.nome.strip().lower(), self.titulo.strip().lower())
