"""Download e parsing dos dados públicos de fundos de investimento da CVM.

Fonte: Portal de Dados Abertos da CVM (https://dados.cvm.gov.br).
- Cadastro de fundos: um CSV único com todos os fundos registrados.
- Informe diário: um CSV por mês com a cota/patrimônio diário de TODOS os
  fundos registrados naquele mês.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

CADASTRO_URL = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv"
INFORME_DIARIO_URL_TEMPLATE = (
    "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{yyyymm}.csv"
)

DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# Classes de fundos que a CVM rotula como "multimercado" no cadastro (CLASSE).
CLASSES_MULTIMERCADO = ("Fundo Multimercado",)


def _baixar_csv(url: str, destino: Path, timeout: int = 60) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        return destino
    resposta = requests.get(url, timeout=timeout)
    resposta.raise_for_status()
    destino.write_bytes(resposta.content)
    return destino


def fetch_cadastro(cache_dir: Path | str = DEFAULT_CACHE_DIR, forcar_download: bool = False) -> pd.DataFrame:
    """Baixa (com cache) e carrega o cadastro completo de fundos da CVM."""
    cache_dir = Path(cache_dir)
    destino = cache_dir / "cad_fi.csv"
    if forcar_download and destino.exists():
        destino.unlink()
    _baixar_csv(CADASTRO_URL, destino)
    return pd.read_csv(destino, sep=";", encoding="latin-1", low_memory=False)


def filtrar_multimercados(cadastro: pd.DataFrame) -> pd.DataFrame:
    """Filtra o cadastro para manter apenas fundos multimercados ativos."""
    df = cadastro[cadastro["CLASSE"].isin(CLASSES_MULTIMERCADO)]
    if "SIT" in df.columns:
        df = df[df["SIT"] == "EM FUNCIONAMENTO NORMAL"]
    return df.reset_index(drop=True)


def fetch_informe_diario(
    ano_mes: str, cache_dir: Path | str = DEFAULT_CACHE_DIR, forcar_download: bool = False
) -> pd.DataFrame:
    """Baixa (com cache) e carrega o informe diário de um mês (ex.: "2026-07").

    Retorna as cotas diárias de TODOS os fundos registrados na CVM naquele
    mês. Filtre pelo CNPJ desejado depois de carregar.
    """
    yyyymm = ano_mes.replace("-", "")[:6]
    cache_dir = Path(cache_dir)
    destino = cache_dir / f"inf_diario_fi_{yyyymm}.csv"
    if forcar_download and destino.exists():
        destino.unlink()
    url = INFORME_DIARIO_URL_TEMPLATE.format(yyyymm=yyyymm)
    _baixar_csv(url, destino)
    df = pd.read_csv(destino, sep=";", encoding="latin-1", low_memory=False)
    df["DT_COMPTC"] = pd.to_datetime(df["DT_COMPTC"])
    return df


def fetch_informe_periodo(
    inicio: str, fim: str, cache_dir: Path | str = DEFAULT_CACHE_DIR
) -> pd.DataFrame:
    """Baixa e concatena o informe diário de todos os meses entre `inicio` e `fim`
    (strings "YYYY-MM" ou "YYYY-MM-DD")."""
    meses = pd.period_range(start=inicio, end=fim, freq="M")
    partes = [fetch_informe_diario(str(mes), cache_dir=cache_dir) for mes in meses]
    return pd.concat(partes, ignore_index=True)


def cotas_do_fundo(informe: pd.DataFrame, cnpj: str) -> pd.Series:
    """Extrai a série de cota diária (VL_QUOTA) de um fundo, indexada por data."""
    df = informe[informe["CNPJ_FUNDO"] == cnpj].sort_values("DT_COMPTC")
    return df.set_index("DT_COMPTC")["VL_QUOTA"]
