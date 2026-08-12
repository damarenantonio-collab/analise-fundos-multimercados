import pandas as pd

from fundos.catalogo import carregar_catalogo, cnpjs, ranking, resumo_por_gestora

CNPJ_REGEX = r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$"


def test_carregar_catalogo_normaliza_colunas():
    df = carregar_catalogo()
    assert "fundo" in df.columns
    assert "cnpj" in df.columns
    assert "sharpe_12m" in df.columns
    assert len(df) > 0


def test_datas_convertidas():
    df = carregar_catalogo()
    assert pd.api.types.is_datetime64_any_dtype(df["inicio_fundo"])
    assert pd.api.types.is_datetime64_any_dtype(df["data_ultima_cota"])
    assert (df["inicio_fundo"] < df["data_ultima_cota"]).all()


def test_cnpjs_formato_cvm():
    df = carregar_catalogo()
    lista = cnpjs(df)
    assert len(lista) == len(df)
    assert all(pd.Series(lista).str.match(CNPJ_REGEX))


def test_ranking_ordena_e_limita():
    df = carregar_catalogo()
    top5 = ranking(df, "sharpe_12m", top_n=5)
    assert len(top5) == 5
    assert list(top5["sharpe_12m"]) == sorted(top5["sharpe_12m"], reverse=True)


def test_ranking_ascendente():
    df = carregar_catalogo()
    menos_volateis = ranking(df, "volatilidade_12m", top_n=3, ascendente=True)
    assert list(menos_volateis["volatilidade_12m"]) == sorted(menos_volateis["volatilidade_12m"])


def test_resumo_por_gestora():
    df = carregar_catalogo()
    resumo = resumo_por_gestora(df)
    assert "n_fundos" in resumo.columns
    assert resumo["n_fundos"].sum() == len(df)
