"""Métricas de risco e retorno para séries de cota de fundos."""
from __future__ import annotations

import numpy as np
import pandas as pd

DIAS_UTEIS_ANO = 252


def retornos_diarios(cotas: pd.Series) -> pd.Series:
    """Retorno percentual diário a partir de uma série de valores de cota."""
    return cotas.sort_index().pct_change().dropna()


def retorno_acumulado(retornos: pd.Series) -> pd.Series:
    """Retorno acumulado (base 1.0) a partir de uma série de retornos diários."""
    return (1 + retornos).cumprod() - 1


def retorno_anualizado(retornos: pd.Series, periodos_por_ano: int = DIAS_UTEIS_ANO) -> float:
    """Retorno anualizado (CAGR) a partir dos retornos diários."""
    n = len(retornos)
    if n == 0:
        return float("nan")
    total = (1 + retornos).prod()
    return total ** (periodos_por_ano / n) - 1


def volatilidade_anualizada(retornos: pd.Series, periodos_por_ano: int = DIAS_UTEIS_ANO) -> float:
    """Desvio-padrão anualizado dos retornos diários."""
    return retornos.std(ddof=1) * np.sqrt(periodos_por_ano)


def indice_sharpe(
    retornos: pd.Series, retornos_livre_risco: pd.Series, periodos_por_ano: int = DIAS_UTEIS_ANO
) -> float:
    """Índice de Sharpe anualizado, usando uma série diária de taxa livre de
    risco (ex.: CDI) alinhada por data ao retorno do fundo."""
    excesso = retornos.align(retornos_livre_risco, join="inner")
    excesso_retorno = excesso[0] - excesso[1]
    if excesso_retorno.std(ddof=1) == 0:
        return float("nan")
    return (excesso_retorno.mean() / excesso_retorno.std(ddof=1)) * np.sqrt(periodos_por_ano)


def max_drawdown(retorno_acum: pd.Series) -> float:
    """Maior queda percentual (drawdown) em relação ao pico anterior,
    a partir de uma série de retorno acumulado (como a de `retorno_acumulado`)."""
    patrimonio = 1 + retorno_acum
    pico = patrimonio.cummax()
    drawdown = patrimonio / pico - 1
    return drawdown.min()


def matriz_correlacao(retornos_por_fundo: dict[str, pd.Series]) -> pd.DataFrame:
    """Matriz de correlação de retornos diários entre vários fundos.

    `retornos_por_fundo` é um dict {nome_do_fundo: série_de_retornos_diários}.
    """
    df = pd.DataFrame(retornos_por_fundo)
    return df.corr()


def resumo(cotas: pd.Series, retornos_livre_risco: pd.Series | None = None) -> dict:
    """Calcula um resumo das principais métricas para uma série de cotas."""
    retornos = retornos_diarios(cotas)
    acumulado = retorno_acumulado(retornos)
    saida = {
        "retorno_total": acumulado.iloc[-1] if len(acumulado) else float("nan"),
        "retorno_anualizado": retorno_anualizado(retornos),
        "volatilidade_anualizada": volatilidade_anualizada(retornos),
        "max_drawdown": max_drawdown(acumulado),
    }
    if retornos_livre_risco is not None:
        saida["sharpe"] = indice_sharpe(retornos, retornos_livre_risco)
    return saida
