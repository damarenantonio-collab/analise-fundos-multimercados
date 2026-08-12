"""Identifica o fundo master de cada fundo feeder (FIC), usando a Composição
e Diversificação das Aplicações (CDA) que a CVM publica mensalmente.

Um fundo "feeder" (FIC - Fundo de Investimento em Cotas) normalmente aplica
quase 100% do seu patrimônio em cotas de um único fundo "master", que executa
a estratégia de fato — é o master que precisa ser analisado para entender o
histórico real da estratégia. Este módulo lê o bloco 2 da CDA
(`cda_fi_BLC_2`, "Cotas de Fundos de Investimento") e, para cada feeder,
escolhe como master a posição em cotas de maior valor de mercado.

Assim como o informe diário, a CDA recente é publicada como CSV solto por
mês; períodos mais antigos ficam em ZIPs anuais na subpasta `HIST/`. A CVM
também costuma levar 1-2 meses para publicar a CDA mais recente, então
`identificar_master` tenta, por padrão, os últimos 6 meses antes de desistir.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from .cvm import (
    DEFAULT_CACHE_DIR,
    _baixar_arquivo,
    _extrair_do_zip,
    coluna_cnpj_fundo,
    fetch_informe_diario,
)

_BASE_CDA = "https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS"
CDA_BLC2_URL_TEMPLATE = f"{_BASE_CDA}/cda_fi_BLC_2_{{yyyymm}}.csv"
CDA_HIST_URL_TEMPLATE = f"{_BASE_CDA}/HIST/cda_fi_{{ano}}.zip"

# Nomes possíveis para as colunas de CNPJ/nome do fundo INVESTIDO (a cota que
# o feeder carrega), em ordem de preferência.
CANDIDATAS_CNPJ_COTA = ("CNPJ_FUNDO_CLASSE_COTA", "CNPJ_FUNDO_COTA")
CANDIDATAS_NOME_COTA = ("NM_FUNDO_CLASSE_SUBCLASSE_COTA", "NM_FUNDO_COTA")


def _coluna(df: pd.DataFrame, candidatas: tuple[str, ...], obrigatoria: bool = True) -> str | None:
    for candidata in candidatas:
        if candidata in df.columns:
            return candidata
    if obrigatoria:
        raise KeyError(f"Nenhuma de {candidatas!r} encontrada. Colunas disponíveis: {list(df.columns)!r}")
    return None


def _baixar_cda_blc2(ano_mes: str, cache_dir: Path | str = DEFAULT_CACHE_DIR) -> pd.DataFrame:
    """Baixa (com cache) e carrega o bloco 2 da CDA (cotas de fundos) de um mês."""
    yyyymm = ano_mes.replace("-", "")[:6]
    ano = yyyymm[:4]
    cache_dir = Path(cache_dir)
    destino = cache_dir / f"cda_fi_BLC_2_{yyyymm}.csv"
    if not destino.exists():
        try:
            _baixar_arquivo(CDA_BLC2_URL_TEMPLATE.format(yyyymm=yyyymm), destino)
        except FileNotFoundError:
            zip_destino = cache_dir / f"cda_fi_{ano}.zip"
            _baixar_arquivo(CDA_HIST_URL_TEMPLATE.format(ano=ano), zip_destino)
            _extrair_do_zip(zip_destino, f"cda_fi_BLC_2_{yyyymm}.csv", destino)
    return pd.read_csv(destino, sep=";", encoding="latin-1", low_memory=False)


def selecionar_master(posicoes_fundo: pd.DataFrame) -> pd.Series | None:
    """Dado o subconjunto da CDA (bloco 2) já filtrado para UM fundo feeder,
    retorna a linha da posição em cotas de maior valor de mercado (o master),
    ou `None` se não houver nenhuma posição em cotas de outro fundo."""
    if posicoes_fundo.empty:
        return None
    coluna_valor = _coluna(posicoes_fundo, ("VL_MERC_POS_FINAL",))
    return posicoes_fundo.sort_values(coluna_valor, ascending=False).iloc[0]


def identificar_master(
    cnpj_feeder: str,
    cache_dir: Path | str = DEFAULT_CACHE_DIR,
    meses_tentativas: int = 6,
) -> dict | None:
    """Procura, a partir do mês mais recente, a posição em cotas do feeder na
    CDA e retorna um dict com `cnpj_master`, `nome_master`, `valor_posicao`,
    `pct_patrimonio_feeder` e `mes_referencia`. Retorna `None` se não achar em
    nenhum dos últimos `meses_tentativas` meses."""
    hoje = pd.Timestamp.today()
    for i in range(1, meses_tentativas + 1):
        mes = (hoje - pd.DateOffset(months=i)).strftime("%Y-%m")
        try:
            blc2 = _baixar_cda_blc2(mes, cache_dir=cache_dir)
        except Exception:  # noqa: BLE001 - tenta o mês anterior
            continue

        coluna_cnpj = coluna_cnpj_fundo(blc2)
        posicoes = blc2[blc2[coluna_cnpj] == cnpj_feeder]
        master = selecionar_master(posicoes)
        if master is None:
            continue

        coluna_valor = _coluna(blc2, ("VL_MERC_POS_FINAL",))
        coluna_cnpj_cota = _coluna(blc2, CANDIDATAS_CNPJ_COTA, obrigatoria=False)
        coluna_nome_cota = _coluna(blc2, CANDIDATAS_NOME_COTA, obrigatoria=False)

        pct_patrimonio = None
        try:
            informe_mes = fetch_informe_diario(mes, cache_dir=cache_dir)
            coluna_cnpj_informe = coluna_cnpj_fundo(informe_mes)
            linha_pl = informe_mes[informe_mes[coluna_cnpj_informe] == cnpj_feeder]
            if len(linha_pl) and "VL_PATRIM_LIQ" in linha_pl.columns:
                pl_feeder = linha_pl["VL_PATRIM_LIQ"].iloc[-1]
                if pl_feeder:
                    pct_patrimonio = master[coluna_valor] / pl_feeder
        except Exception:  # noqa: BLE001 - pct fica None, mas o master já foi achado
            pass

        return {
            "cnpj_master": master.get(coluna_cnpj_cota) if coluna_cnpj_cota else None,
            "nome_master": master.get(coluna_nome_cota) if coluna_nome_cota else None,
            "valor_posicao": master[coluna_valor],
            "pct_patrimonio_feeder": pct_patrimonio,
            "mes_referencia": mes,
        }
    return None


def identificar_masters_catalogo(
    catalogo: pd.DataFrame,
    cache_dir: Path | str = DEFAULT_CACHE_DIR,
    pausa_seg: float = 0.5,
    verbose: bool = True,
) -> pd.DataFrame:
    """Roda `identificar_master` para cada fundo do catálogo (`fundo`, `cnpj`).
    Segue mesmo se algum fundo falhar — o motivo fica na coluna `erro`."""
    linhas = []
    for _, fundo in catalogo.iterrows():
        if verbose:
            print(f"Buscando master de: {fundo['fundo']} ({fundo['cnpj']})...")
        try:
            resultado = identificar_master(fundo["cnpj"], cache_dir=cache_dir)
        except Exception as erro:  # noqa: BLE001 - registra e segue para o próximo fundo
            linhas.append({"fundo": fundo["fundo"], "cnpj_feeder": fundo["cnpj"], "erro": str(erro)})
            continue
        if resultado is None:
            linhas.append(
                {"fundo": fundo["fundo"], "cnpj_feeder": fundo["cnpj"], "erro": "master não encontrado na CDA"}
            )
        else:
            linhas.append({"fundo": fundo["fundo"], "cnpj_feeder": fundo["cnpj"], **resultado})
        time.sleep(pausa_seg)
    return pd.DataFrame(linhas)
