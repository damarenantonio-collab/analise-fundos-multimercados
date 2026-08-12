"""Carrega o catálogo de fundos multimercados usado como universo do estudo
(planilha `data/catalogo_fundos_multimercados.xlsx`, no formato exportado pela
plataforma BTG: um fundo por linha, com CNPJ, classificações, taxas e métricas
de performance já calculadas pela distribuidora).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_CAMINHO = Path(__file__).resolve().parents[2] / "data" / "catalogo_fundos_multimercados.xlsx"

EPOCH_EXCEL = "1899-12-30"

# De -> Para: nomes originais da planilha -> nomes normalizados (snake_case).
RENOMEAR_COLUNAS = {
    "Fundo": "fundo",
    "CGE": "cge",
    "CNPJ": "cnpj",
    "Top Funds": "top_funds",
    "Segmento": "segmento",
    "Categoria BTG": "categoria_btg",
    "Subcategoria BTG": "subcategoria_btg",
    "ESG": "esg",
    "Quantitativos": "quantitativos",
    "Temáticos": "tematicos",
    "Indexados": "indexados",
    "Internacionais": "internacionais",
    "Hedge Cambial": "hedge_cambial",
    "Suitability BTG": "suitability_btg",
    "Gestão": "gestora",
    "Administrador": "administrador",
    "Custodiante": "custodiante",
    "Público Alvo": "publico_alvo",
    "Classificação CVM": "classificacao_cvm",
    "Classificação Anbima": "classificacao_anbima",
    "Classificação Tributária": "classificacao_tributaria",
    "Aplicação": "aplicacao",
    "Aplicação Minima": "aplicacao_minima",
    "Movimentação Minima": "movimentacao_minima",
    "Saldo Minimo": "saldo_minimo",
    "Horário de Aplicação": "horario_aplicacao",
    "Horário de Resgate": "horario_resgate",
    "Divulgação (Perfil)": "divulgacao_perfil",
    "Liquidez (Cotização + Liquidação dos Recursos Resgatados) D+": "liquidez_dias",
    "Taxa De Administração": "taxa_administracao",
    "Taxa de Administração (Máxima)": "taxa_administracao_maxima",
    "Taxa De Gestão": "taxa_gestao",
    "Taxa De Distribuição": "taxa_distribuicao",
    "Taxa De Performance": "taxa_performance",
    "Benchmark": "benchmark",
    "Início Do Fundo": "inicio_fundo",
    "Data da Última Cota": "data_ultima_cota",
    "Retorno Nominal - Mês": "retorno_nominal_mes",
    "Retorno Nominal - Ano": "retorno_nominal_ano",
    "Retorno Nominal - 12 M": "retorno_nominal_12m",
    "Retorno Nominal - 24 M": "retorno_nominal_24m",
    "Retorno Nominal - 36 M": "retorno_nominal_36m",
    "Retorno Nominal - 2025": "retorno_nominal_2025",
    "Retorno Nominal - 2024": "retorno_nominal_2024",
    "Retorno Nominal - 2023": "retorno_nominal_2023",
    "Retorno % do CDI - 12 M": "retorno_pct_cdi_12m",
    "Retorno % do CDI - 24 M": "retorno_pct_cdi_24m",
    "Retorno % do CDI - 36 M": "retorno_pct_cdi_36m",
    "Retorno % do CDI - 2025": "retorno_pct_cdi_2025",
    "Retorno % do CDI - 2024": "retorno_pct_cdi_2024",
    "Retorno % do CDI - 2023": "retorno_pct_cdi_2023",
    "Volatilidade 12 M": "volatilidade_12m",
    "Sharpe 12 M": "sharpe_12m",
    "Patrimônio Líquido": "patrimonio_liquido",
    "ISIN": "isin",
    "RoA Adm - B2B": "roa_adm_b2b",
    "RoA Perf - B2B": "roa_perf_b2b",
}

COLUNAS_DATA_EXCEL = ("inicio_fundo", "data_ultima_cota")


def carregar_catalogo(caminho: str | Path = DEFAULT_CAMINHO) -> pd.DataFrame:
    """Carrega o catálogo de fundos, normaliza nomes de coluna e converte as
    datas (armazenadas como serial do Excel) para `datetime`."""
    df = pd.read_excel(caminho)
    df = df.rename(columns=RENOMEAR_COLUNAS)
    for coluna in COLUNAS_DATA_EXCEL:
        if coluna in df.columns:
            df[coluna] = pd.to_datetime(df[coluna], unit="D", origin=EPOCH_EXCEL).dt.normalize()
    return df


def cnpjs(catalogo: pd.DataFrame) -> list[str]:
    """Lista de CNPJs do catálogo, no mesmo formato usado pelos dados da CVM
    (ex.: "12.345.678/0001-90")."""
    return catalogo["cnpj"].tolist()


def ranking(
    catalogo: pd.DataFrame, coluna: str, top_n: int = 10, ascendente: bool = False
) -> pd.DataFrame:
    """Ranking dos fundos por uma coluna de métrica (ex.: "sharpe_12m",
    "retorno_pct_cdi_12m", "volatilidade_12m")."""
    return (
        catalogo[["fundo", "gestora", coluna]]
        .sort_values(coluna, ascending=ascendente)
        .head(top_n)
        .reset_index(drop=True)
    )


def resumo_por_gestora(catalogo: pd.DataFrame) -> pd.DataFrame:
    """Agrupa o catálogo por gestora: nº de fundos, patrimônio total e médias
    de retorno/volatilidade/Sharpe (12 meses)."""
    return (
        catalogo.groupby("gestora")
        .agg(
            n_fundos=("fundo", "count"),
            patrimonio_total=("patrimonio_liquido", "sum"),
            retorno_12m_medio=("retorno_nominal_12m", "mean"),
            volatilidade_12m_media=("volatilidade_12m", "mean"),
            sharpe_12m_medio=("sharpe_12m", "mean"),
        )
        .sort_values("patrimonio_total", ascending=False)
    )
