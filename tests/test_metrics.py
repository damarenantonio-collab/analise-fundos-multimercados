import numpy as np
import pandas as pd
import pytest

from fundos.metrics import (
    indice_sharpe,
    matriz_correlacao,
    max_drawdown,
    retorno_acumulado,
    retorno_anualizado,
    retornos_diarios,
    volatilidade_anualizada,
)


def _datas(n):
    return pd.date_range("2026-01-01", periods=n, freq="B")


def test_retornos_diarios():
    cotas = pd.Series([1.0, 1.01, 1.0201], index=_datas(3))
    retornos = retornos_diarios(cotas)
    assert len(retornos) == 2
    np.testing.assert_allclose(retornos.values, [0.01, 0.01], atol=1e-9)


def test_retorno_acumulado():
    retornos = pd.Series([0.01, 0.01, -0.02], index=_datas(3))
    acumulado = retorno_acumulado(retornos)
    esperado = (1.01 * 1.01 * 0.98) - 1
    assert acumulado.iloc[-1] == pytest.approx(esperado)


def test_retorno_anualizado_constante():
    # retorno diário constante de 0.01 por ~1 ano útil -> deve compor para o total
    retornos = pd.Series([0.01] * 252, index=_datas(252))
    anualizado = retorno_anualizado(retornos, periodos_por_ano=252)
    assert anualizado == pytest.approx((1.01 ** 252) - 1)


def test_volatilidade_anualizada_positiva():
    retornos = pd.Series([0.01, -0.01, 0.02, -0.02, 0.0], index=_datas(5))
    vol = volatilidade_anualizada(retornos, periodos_por_ano=252)
    assert vol > 0


def test_max_drawdown():
    # patrimônio sobe para 1.10, cai para 0.99 -> drawdown de (0.99/1.10 - 1)
    retornos = pd.Series([0.10, -0.10], index=_datas(2))
    acumulado = retorno_acumulado(retornos)
    dd = max_drawdown(acumulado)
    assert dd == pytest.approx((0.99 / 1.10) - 1)


def test_indice_sharpe_zero_quando_igual_ao_livre_de_risco():
    datas = _datas(5)
    retornos = pd.Series([0.001] * 5, index=datas)
    livre_risco = pd.Series([0.001] * 5, index=datas)
    sharpe = indice_sharpe(retornos, livre_risco)
    assert np.isnan(sharpe)


def test_matriz_correlacao_diagonal_um():
    datas = _datas(5)
    a = pd.Series([0.01, 0.02, -0.01, 0.0, 0.03], index=datas)
    b = pd.Series([0.02, 0.04, -0.02, 0.0, 0.06], index=datas)
    matriz = matriz_correlacao({"fundo_a": a, "fundo_b": b})
    assert matriz.loc["fundo_a", "fundo_a"] == 1.0
    np.testing.assert_allclose(matriz.loc["fundo_a", "fundo_b"], 1.0, atol=1e-9)
