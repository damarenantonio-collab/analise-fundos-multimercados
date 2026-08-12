"""Download e parsing dos dados públicos de fundos de investimento da CVM.

Fonte: Portal de Dados Abertos da CVM (https://dados.cvm.gov.br).
- Cadastro de fundos: um CSV único com todos os fundos registrados.
- Informe diário: um CSV por mês com a cota/patrimônio diário de TODOS os
  fundos registrados naquele mês. Apenas os últimos meses ficam disponíveis
  como CSV solto; períodos mais antigos são publicados em ZIPs anuais na
  subpasta `HIST/` (mesmo schema, um CSV por mês dentro do ZIP). As funções
  aqui tentam primeiro o CSV solto e caem para o ZIP anual automaticamente.

Atenção: a CVM alterou alguns nomes de coluna ao longo do tempo (ex.:
`CNPJ_FUNDO` -> `CNPJ_FUNDO_CLASSE` para fundos estruturados em classes desde
a reforma de 2023). As funções abaixo detectam a coluna correta dinamicamente
via `coluna_cnpj_fundo`; se a CVM mudar novamente o layout, ajuste as
constantes/candidatas no topo deste arquivo.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd
import requests

CADASTRO_URL = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv"

_BASE_INF_DIARIO = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS"
INFORME_DIARIO_URL_TEMPLATE = f"{_BASE_INF_DIARIO}/inf_diario_fi_{{yyyymm}}.csv"
INFORME_DIARIO_HIST_URL_TEMPLATE = f"{_BASE_INF_DIARIO}/HIST/inf_diario_fi_{{ano}}.zip"

DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# Classes de fundos que a CVM rotula como "multimercado" no cadastro (CLASSE).
CLASSES_MULTIMERCADO = ("Fundo Multimercado",)

# Nomes possíveis da coluna de CNPJ do fundo, em ordem de preferência.
CANDIDATAS_COLUNA_CNPJ = ("CNPJ_FUNDO_CLASSE", "CNPJ_FUNDO")

# Nomes possíveis da coluna de data de início de atividade no cadastro.
CANDIDATAS_COLUNA_DATA_INICIO = ("DT_INI_ATIV", "DT_REG")


def _baixar_arquivo(url: str, destino: Path, timeout: int = 60) -> Path:
    """Baixa `url` para `destino` (com cache: não baixa de novo se já existe).
    Levanta `FileNotFoundError` em 404, para permitir fallback para outra URL."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        return destino
    resposta = requests.get(url, timeout=timeout)
    if resposta.status_code == 404:
        raise FileNotFoundError(url)
    resposta.raise_for_status()
    destino.write_bytes(resposta.content)
    return destino


def _extrair_do_zip(caminho_zip: Path, nome_arquivo: str, destino: Path) -> Path:
    """Extrai de `caminho_zip` o membro cujo nome termina com `nome_arquivo`."""
    if destino.exists():
        return destino
    with zipfile.ZipFile(caminho_zip) as zf:
        candidatos = [n for n in zf.namelist() if n.endswith(nome_arquivo)]
        if not candidatos:
            raise FileNotFoundError(f"{nome_arquivo} não encontrado dentro de {caminho_zip.name}")
        destino.write_bytes(zf.read(candidatos[0]))
    return destino


def coluna_cnpj_fundo(df: pd.DataFrame) -> str:
    """Detecta o nome da coluna de CNPJ do fundo num DataFrame vindo da CVM
    (varia entre `CNPJ_FUNDO` e `CNPJ_FUNDO_CLASSE` conforme o layout)."""
    for candidata in CANDIDATAS_COLUNA_CNPJ:
        if candidata in df.columns:
            return candidata
    raise KeyError(
        f"Nenhuma coluna de CNPJ encontrada entre {CANDIDATAS_COLUNA_CNPJ!r}. "
        f"Colunas disponíveis: {list(df.columns)!r}"
    )


def fetch_cadastro(cache_dir: Path | str = DEFAULT_CACHE_DIR, forcar_download: bool = False) -> pd.DataFrame:
    """Baixa (com cache) e carrega o cadastro completo de fundos da CVM."""
    cache_dir = Path(cache_dir)
    destino = cache_dir / "cad_fi.csv"
    if forcar_download and destino.exists():
        destino.unlink()
    _baixar_arquivo(CADASTRO_URL, destino)
    return pd.read_csv(destino, sep=";", encoding="latin-1", low_memory=False)


def filtrar_multimercados(cadastro: pd.DataFrame) -> pd.DataFrame:
    """Filtra o cadastro para manter apenas fundos multimercados ativos."""
    df = cadastro[cadastro["CLASSE"].isin(CLASSES_MULTIMERCADO)]
    if "SIT" in df.columns:
        df = df[df["SIT"] == "EM FUNCIONAMENTO NORMAL"]
    return df.reset_index(drop=True)


def data_inicio_atividade(cadastro: pd.DataFrame, cnpj: str) -> pd.Timestamp | None:
    """Data de início de atividade de um fundo, a partir do cadastro da CVM.
    Retorna `None` se o CNPJ não estiver no cadastro ou não houver data."""
    coluna_cnpj = coluna_cnpj_fundo(cadastro)
    linha = cadastro[cadastro[coluna_cnpj] == cnpj]
    if linha.empty:
        return None
    for candidata in CANDIDATAS_COLUNA_DATA_INICIO:
        if candidata in cadastro.columns:
            valor = linha.iloc[0][candidata]
            if pd.notna(valor):
                return pd.to_datetime(valor)
    return None


def fetch_informe_diario(
    ano_mes: str, cache_dir: Path | str = DEFAULT_CACHE_DIR, forcar_download: bool = False
) -> pd.DataFrame:
    """Baixa (com cache) e carrega o informe diário de um mês (ex.: "2026-07").

    Tenta primeiro o CSV mensal solto; se a CVM já tiver movido esse mês para
    o arquivo histórico anual (`HIST/inf_diario_fi_{ano}.zip`), cai para ele
    automaticamente.

    Retorna as cotas diárias de TODOS os fundos registrados na CVM naquele
    mês. Filtre pelo CNPJ desejado depois de carregar (veja `cotas_do_fundo`).
    """
    yyyymm = ano_mes.replace("-", "")[:6]
    ano = yyyymm[:4]
    cache_dir = Path(cache_dir)
    destino = cache_dir / f"inf_diario_fi_{yyyymm}.csv"
    if forcar_download and destino.exists():
        destino.unlink()
    if not destino.exists():
        try:
            _baixar_arquivo(INFORME_DIARIO_URL_TEMPLATE.format(yyyymm=yyyymm), destino)
        except FileNotFoundError:
            zip_destino = cache_dir / f"inf_diario_fi_{ano}.zip"
            _baixar_arquivo(INFORME_DIARIO_HIST_URL_TEMPLATE.format(ano=ano), zip_destino)
            _extrair_do_zip(zip_destino, f"inf_diario_fi_{yyyymm}.csv", destino)
    df = pd.read_csv(destino, sep=";", encoding="latin-1", low_memory=False)
    df["DT_COMPTC"] = pd.to_datetime(df["DT_COMPTC"])
    return df


def fetch_informe_periodo(
    inicio: str, fim: str, cache_dir: Path | str = DEFAULT_CACHE_DIR
) -> pd.DataFrame:
    """Baixa e concatena o informe diário de todos os meses entre `inicio` e `fim`
    (strings "YYYY-MM" ou "YYYY-MM-DD"). Carrega o universo inteiro de fundos
    de cada mês em memória — para períodos longos (vários anos), prefira
    `fetch_serie_historica`, que filtra por CNPJ mês a mês."""
    meses = pd.period_range(start=inicio, end=fim, freq="M")
    partes = [fetch_informe_diario(str(mes), cache_dir=cache_dir) for mes in meses]
    return pd.concat(partes, ignore_index=True)


def cotas_do_fundo(informe: pd.DataFrame, cnpj: str) -> pd.Series:
    """Extrai a série de cota diária (VL_QUOTA) de um fundo, indexada por data."""
    coluna_cnpj = coluna_cnpj_fundo(informe)
    df = informe[informe[coluna_cnpj] == cnpj].sort_values("DT_COMPTC")
    return df.set_index("DT_COMPTC")["VL_QUOTA"]


def fetch_serie_historica(
    cnpj: str,
    data_inicio: str,
    data_fim: str | None = None,
    cache_dir: Path | str = DEFAULT_CACHE_DIR,
    verbose: bool = True,
) -> pd.Series:
    """Busca a série completa de cota diária (VL_QUOTA) de um fundo entre
    `data_inicio` e `data_fim` (default: hoje), mês a mês.

    Diferente de `fetch_informe_periodo` + `cotas_do_fundo`, filtra pelo CNPJ
    logo após carregar cada mês (em vez de concatenar o universo inteiro de
    fundos de todos os meses), o que é essencial para históricos longos
    (fundos com 10+ anos de existência = 120+ arquivos mensais).

    Meses que falharem ao baixar são pulados com um aviso, para que uma falha
    pontual não derrube a série inteira.
    """
    fim = pd.Timestamp(data_fim) if data_fim else pd.Timestamp.today()
    coluna_cnpj_alvo: str | None = None
    meses = pd.period_range(start=data_inicio, end=fim, freq="M")
    partes = []
    for mes in meses:
        try:
            informe_mes = fetch_informe_diario(str(mes), cache_dir=cache_dir)
        except Exception as erro:  # noqa: BLE001 - segue para o próximo mês
            if verbose:
                print(f"  aviso: falha ao buscar informe de {mes} ({erro}); pulando")
            continue
        if coluna_cnpj_alvo is None or coluna_cnpj_alvo not in informe_mes.columns:
            coluna_cnpj_alvo = coluna_cnpj_fundo(informe_mes)
        cotas_mes = informe_mes[informe_mes[coluna_cnpj_alvo] == cnpj]
        if len(cotas_mes):
            partes.append(cotas_mes[["DT_COMPTC", "VL_QUOTA"]])
    if not partes:
        return pd.Series(dtype=float, name="VL_QUOTA")
    todas = pd.concat(partes, ignore_index=True).sort_values("DT_COMPTC")
    return todas.set_index("DT_COMPTC")["VL_QUOTA"]
