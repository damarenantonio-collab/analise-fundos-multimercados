"""Carregamento de planilhas próprias (CSV/XLSX) com cotas de fundos.

Aceita nomes de coluna variados e normaliza para um schema único:
`data` (datetime), `fundo` (str), `valor_cota` (float).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUNAS_DATA = ("data", "dt_comptc", "date")
COLUNAS_FUNDO = ("fundo", "nome", "name", "denom_social", "cnpj_fundo")
COLUNAS_COTA = ("valor_cota", "cota", "vl_quota", "valor da cota", "quota", "valor")


def _achar_coluna(colunas: list[str], candidatas: tuple[str, ...]) -> str:
    normalizadas = {c.strip().lower(): c for c in colunas}
    for candidata in candidatas:
        if candidata in normalizadas:
            return normalizadas[candidata]
    raise ValueError(
        f"Nenhuma coluna encontrada entre {candidatas!r}. Colunas disponíveis: {colunas!r}"
    )


def carregar_carteira(caminho: str | Path) -> pd.DataFrame:
    """Lê um CSV ou XLSX com cotas de um ou mais fundos e retorna um DataFrame
    padronizado com colunas `data`, `fundo`, `valor_cota`, ordenado por fundo e data.
    """
    caminho = Path(caminho)
    if caminho.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(caminho)
    else:
        df = pd.read_csv(caminho)

    colunas = list(df.columns)
    col_data = _achar_coluna(colunas, COLUNAS_DATA)
    col_fundo = _achar_coluna(colunas, COLUNAS_FUNDO)
    col_cota = _achar_coluna(colunas, COLUNAS_COTA)

    padronizado = pd.DataFrame(
        {
            "data": pd.to_datetime(df[col_data]),
            "fundo": df[col_fundo].astype(str),
            "valor_cota": pd.to_numeric(df[col_cota], errors="coerce"),
        }
    ).dropna(subset=["valor_cota"])

    return padronizado.sort_values(["fundo", "data"]).reset_index(drop=True)


def serie_do_fundo(carteira: pd.DataFrame, nome_fundo: str) -> pd.Series:
    """Extrai a série de cota diária de um fundo específico, indexada por data."""
    df = carteira[carteira["fundo"] == nome_fundo].sort_values("data")
    return df.set_index("data")["valor_cota"]
