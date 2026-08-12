"""Séries de benchmark (CDI, IPCA) via API de Séries Temporais do Banco Central (SGS).

Documentação: https://dadosabertos.bcb.gov.br/dataset/12-taxa-de-juros---cdi
"""
from __future__ import annotations

import pandas as pd
import requests

SGS_URL_TEMPLATE = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
    "?formato=json&dataInicial={inicio}&dataFinal={fim}"
)

CODIGO_CDI = 12      # Taxa de juros - CDI, % ao dia
CODIGO_IPCA = 433    # IPCA, variação % mensal


def _formatar_data_br(data: str) -> str:
    return pd.to_datetime(data).strftime("%d/%m/%Y")


def fetch_bcb_series(codigo: int, inicio: str, fim: str, timeout: int = 30) -> pd.Series:
    """Busca uma série do SGS/BCB e retorna como fração decimal (não percentual),
    indexada por data."""
    url = SGS_URL_TEMPLATE.format(
        codigo=codigo, inicio=_formatar_data_br(inicio), fim=_formatar_data_br(fim)
    )
    resposta = requests.get(url, timeout=timeout)
    resposta.raise_for_status()
    dados = resposta.json()
    serie = pd.Series(
        {pd.to_datetime(item["data"], dayfirst=True): float(item["valor"]) / 100 for item in dados}
    ).sort_index()
    serie.index.name = "data"
    return serie


def cdi_diario(inicio: str, fim: str) -> pd.Series:
    """Taxa CDI diária (fração decimal, ex.: 0.00045 = 0,045% no dia)."""
    return fetch_bcb_series(CODIGO_CDI, inicio, fim)


def ipca_mensal(inicio: str, fim: str) -> pd.Series:
    """Variação mensal do IPCA (fração decimal)."""
    return fetch_bcb_series(CODIGO_IPCA, inicio, fim)
