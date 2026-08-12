import pandas as pd
import pytest

from fundos.cvm import coluna_cnpj_fundo


def test_coluna_cnpj_fundo_formato_antigo():
    df = pd.DataFrame({"CNPJ_FUNDO": ["00.000.000/0001-00"]})
    assert coluna_cnpj_fundo(df) == "CNPJ_FUNDO"


def test_coluna_cnpj_fundo_formato_novo_com_classes():
    df = pd.DataFrame({"CNPJ_FUNDO_CLASSE": ["00.000.000/0001-00"]})
    assert coluna_cnpj_fundo(df) == "CNPJ_FUNDO_CLASSE"


def test_coluna_cnpj_fundo_prefere_classe_quando_ambas_existem():
    df = pd.DataFrame({"CNPJ_FUNDO": ["a"], "CNPJ_FUNDO_CLASSE": ["b"]})
    assert coluna_cnpj_fundo(df) == "CNPJ_FUNDO_CLASSE"


def test_coluna_cnpj_fundo_ausente_gera_erro():
    with pytest.raises(KeyError):
        coluna_cnpj_fundo(pd.DataFrame({"OUTRA_COLUNA": ["x"]}))
