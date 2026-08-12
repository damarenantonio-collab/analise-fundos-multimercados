from pathlib import Path

from fundos.loaders import carregar_carteira, serie_do_fundo

EXEMPLO = Path(__file__).resolve().parents[1] / "examples" / "minha_carteira.csv"


def test_carregar_carteira_normaliza_colunas():
    carteira = carregar_carteira(EXEMPLO)
    assert list(carteira.columns) == ["data", "fundo", "valor_cota"]
    assert carteira["valor_cota"].dtype.kind == "f"
    assert carteira["fundo"].nunique() >= 1


def test_serie_do_fundo():
    carteira = carregar_carteira(EXEMPLO)
    nome = carteira["fundo"].iloc[0]
    serie = serie_do_fundo(carteira, nome)
    assert serie.index.is_monotonic_increasing
    assert len(serie) > 0
