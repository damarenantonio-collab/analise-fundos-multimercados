import pandas as pd

from fundos.master import selecionar_master


def test_selecionar_master_escolhe_maior_posicao():
    posicoes = pd.DataFrame(
        {
            "CNPJ_FUNDO": ["11.111.111/0001-11", "11.111.111/0001-11"],
            "CNPJ_FUNDO_CLASSE_COTA": ["22.222.222/0001-22", "33.333.333/0001-33"],
            "NM_FUNDO_CLASSE_SUBCLASSE_COTA": ["Fundo Master A", "Fundo Master B"],
            "VL_MERC_POS_FINAL": [1_000_000.0, 50_000_000.0],
        }
    )
    master = selecionar_master(posicoes)
    assert master["NM_FUNDO_CLASSE_SUBCLASSE_COTA"] == "Fundo Master B"
    assert master["CNPJ_FUNDO_CLASSE_COTA"] == "33.333.333/0001-33"


def test_selecionar_master_posicao_unica():
    posicoes = pd.DataFrame(
        {
            "CNPJ_FUNDO": ["11.111.111/0001-11"],
            "CNPJ_FUNDO_CLASSE_COTA": ["22.222.222/0001-22"],
            "NM_FUNDO_CLASSE_SUBCLASSE_COTA": ["Fundo Master Único"],
            "VL_MERC_POS_FINAL": [10_000_000.0],
        }
    )
    master = selecionar_master(posicoes)
    assert master["NM_FUNDO_CLASSE_SUBCLASSE_COTA"] == "Fundo Master Único"


def test_selecionar_master_vazio_retorna_none():
    assert selecionar_master(pd.DataFrame()) is None
