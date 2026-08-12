import pandas as pd

from fundos.benchmarks import _janelas


def test_janelas_intervalo_curto_uma_janela():
    janelas = _janelas("2026-01-01", "2026-01-10", max_dias=3650)
    assert janelas == [(pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-10"))]


def test_janelas_intervalo_longo_cobre_tudo_sem_buracos_nem_sobreposicao():
    janelas = _janelas("2000-01-01", "2026-01-01", max_dias=3650)
    assert len(janelas) > 1
    assert janelas[0][0] == pd.Timestamp("2000-01-01")
    assert janelas[-1][1] == pd.Timestamp("2026-01-01")
    for (_, fim_atual), (proximo_inicio, _) in zip(janelas, janelas[1:]):
        assert proximo_inicio == fim_atual + pd.Timedelta(days=1)


def test_janelas_max_dias_respeitado():
    janelas = _janelas("2000-01-01", "2026-01-01", max_dias=3650)
    for inicio, fim in janelas:
        assert (fim - inicio).days < 3650
