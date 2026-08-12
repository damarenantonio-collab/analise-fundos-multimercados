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

# O SGS/BCB limita o intervalo de datas por chamada; para séries "desde o
# início" de fundos antigos (10+ anos), buscamos em janelas e concatenamos.
MAX_DIAS_POR_JANELA = 3650  # ~10 anos


def _formatar_data_br(data) -> str:
    return pd.to_datetime(data).strftime("%d/%m/%Y")


def _janelas(inicio: str, fim: str, max_dias: int = MAX_DIAS_POR_JANELA) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Divide [inicio, fim] em janelas consecutivas de no máximo `max_dias`,
    sem sobreposição e sem buracos."""
    inicio_ts = pd.Timestamp(inicio)
    fim_ts = pd.Timestamp(fim)
    janelas = []
    cursor = inicio_ts
    while cursor <= fim_ts:
        fim_janela = min(cursor + pd.Timedelta(days=max_dias - 1), fim_ts)
        janelas.append((cursor, fim_janela))
        cursor = fim_janela + pd.Timedelta(days=1)
    return janelas


def fetch_bcb_series(codigo: int, inicio: str, fim: str, timeout: int = 30) -> pd.Series:
    """Busca uma série do SGS/BCB e retorna como fração decimal (não percentual),
    indexada por data. Divide automaticamente em janelas para intervalos longos."""
    partes = []
    for inicio_janela, fim_janela in _janelas(inicio, fim):
        url = SGS_URL_TEMPLATE.format(
            codigo=codigo,
            inicio=_formatar_data_br(inicio_janela),
            fim=_formatar_data_br(fim_janela),
        )
        resposta = requests.get(url, timeout=timeout)
        resposta.raise_for_status()
        dados = resposta.json()
        if dados:
            partes.append(
                pd.Series(
                    {pd.to_datetime(item["data"], dayfirst=True): float(item["valor"]) / 100 for item in dados}
                )
            )
    if not partes:
        return pd.Series(dtype=float, name="data")
    serie = pd.concat(partes).sort_index()
    serie.index.name = "data"
    return serie


def cdi_diario(inicio: str, fim: str) -> pd.Series:
    """Taxa CDI diária (fração decimal, ex.: 0.00045 = 0,045% no dia)."""
    return fetch_bcb_series(CODIGO_CDI, inicio, fim)


def ipca_mensal(inicio: str, fim: str) -> pd.Series:
    """Variação mensal do IPCA (fração decimal)."""
    return fetch_bcb_series(CODIGO_IPCA, inicio, fim)
