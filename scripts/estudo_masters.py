#!/usr/bin/env python3
"""Identifica o fundo master de cada fundo do catálogo e calcula o retorno
histórico do master desde o início da sua série na CVM.

Requer rede (dados.cvm.gov.br e api.bcb.gov.br) — rode localmente ou em CI
com acesso liberado:

    python scripts/estudo_masters.py

Saídas em data/processed/:
    masters.csv                  - master identificado (ou erro) por fundo do catálogo
    retorno_historico_masters.csv - métricas de cada master desde o início
    series_masters.csv            - série diária de retorno acumulado de cada master

Pode demorar: para fundos com muitos anos de histórico, busca um arquivo por
mês na CVM (com cache local em data/raw/, então reexecuções são rápidas).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from fundos.benchmarks import cdi_diario  # noqa: E402
from fundos.catalogo import carregar_catalogo  # noqa: E402
from fundos.cvm import data_inicio_atividade, fetch_cadastro, fetch_serie_historica  # noqa: E402
from fundos.master import identificar_masters_catalogo  # noqa: E402
from fundos.metrics import resumo, retorno_acumulado, retornos_diarios  # noqa: E402

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


def main() -> None:
    catalogo = carregar_catalogo()

    print(f"Identificando o fundo master de {len(catalogo)} fundos via CDA da CVM...")
    masters = identificar_masters_catalogo(catalogo)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    masters.to_csv(PROCESSED_DIR / "masters.csv", index=False)
    print(f"Salvo em {PROCESSED_DIR / 'masters.csv'}")

    if "cnpj_master" not in masters.columns:
        print("\nNenhum master encontrado para nenhum fundo. Veja masters.csv para os erros.")
        return

    encontrados = masters.dropna(subset=["cnpj_master"])
    print(f"\nMaster encontrado para {len(encontrados)}/{len(catalogo)} fundos.")
    if encontrados.empty:
        return

    print("\nBaixando cadastro da CVM (para a data de início de cada master)...")
    cadastro = fetch_cadastro()

    resultados = []
    series = []
    for _, linha in encontrados.drop_duplicates("cnpj_master").iterrows():
        cnpj_master = linha["cnpj_master"]
        nome_master = linha["nome_master"]
        inicio = data_inicio_atividade(cadastro, cnpj_master)
        if inicio is None:
            print(f"  aviso: sem data de início cadastrada para {nome_master} ({cnpj_master}); pulando")
            continue

        print(f"  {nome_master}: histórico desde {inicio.date()}...")
        cotas = fetch_serie_historica(cnpj_master, str(inicio.date()))
        if cotas.empty:
            print("    sem cotas retornadas; pulando")
            continue

        cdi = cdi_diario(str(inicio.date()), str(cotas.index.max().date()))
        metricas = resumo(cotas, retornos_livre_risco=cdi)
        resultados.append(
            {
                "cnpj_master": cnpj_master,
                "nome_master": nome_master,
                "data_inicio": inicio.date(),
                "data_ultima_cota": cotas.index.max().date(),
                "n_dias_uteis": len(cotas) - 1,
                **metricas,
            }
        )

        acumulado = retorno_acumulado(retornos_diarios(cotas))
        series.append(
            pd.DataFrame(
                {
                    "cnpj_master": cnpj_master,
                    "nome_master": nome_master,
                    "data": acumulado.index,
                    "retorno_acumulado": acumulado.values,
                }
            )
        )

    if resultados:
        df_resultados = pd.DataFrame(resultados).sort_values("retorno_anualizado", ascending=False)
        df_resultados.to_csv(PROCESSED_DIR / "retorno_historico_masters.csv", index=False)
        print(f"\nSalvo em {PROCESSED_DIR / 'retorno_historico_masters.csv'}")
        print(df_resultados.to_string(index=False))
    else:
        print("\nNenhum master teve histórico calculado com sucesso.")

    if series:
        pd.concat(series, ignore_index=True).to_csv(PROCESSED_DIR / "series_masters.csv", index=False)
        print(f"Séries diárias salvas em {PROCESSED_DIR / 'series_masters.csv'}")


if __name__ == "__main__":
    main()
