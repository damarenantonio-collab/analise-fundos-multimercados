#!/usr/bin/env python3
"""Diagnóstico: baixa a CDA (bloco 2 - cotas de fundos) de alguns meses
recentes e mostra o schema real (colunas) e se um fundo conhecido aparece.
Rode isto quando `identificar_masters_catalogo` não encontrar nenhum master
- ajuda a ver se é problema de URL/download ou de nome de coluna.

    python scripts/diagnostico_cda.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fundos.cvm import coluna_cnpj_fundo  # noqa: E402
from fundos.master import _baixar_cda_blc2  # noqa: E402

CNPJ_CONHECIDO = "24.029.438/0001-60"  # Adam Macro II FICFIM RL, do catálogo
NOME_CONHECIDO = "Adam Macro II FICFIM RL"

MESES_PARA_TENTAR = ["2026-06", "2026-05", "2026-04", "2026-03", "2026-02", "2026-01"]


def main() -> None:
    for mes in MESES_PARA_TENTAR:
        print(f"\n--- tentando CDA de {mes} ---")
        try:
            df = _baixar_cda_blc2(mes)
        except Exception as erro:
            print(f"FALHOU AO BAIXAR: {type(erro).__name__}: {erro}")
            continue

        print(f"download OK. shape={df.shape}")
        print(f"colunas ({len(df.columns)}): {list(df.columns)}")

        try:
            col_cnpj = coluna_cnpj_fundo(df)
        except KeyError as erro:
            print(f"NÃO ACHEI COLUNA DE CNPJ: {erro}")
            continue
        print(f"coluna de CNPJ usada: {col_cnpj}")

        sub = df[df[col_cnpj] == CNPJ_CONHECIDO]
        print(f"linhas para {NOME_CONHECIDO} ({CNPJ_CONHECIDO}): {len(sub)}")
        if len(sub):
            print(sub.to_string())
            print("\n>>> achou dados! esse é o mês/schema a usar.")
            return
        else:
            amostra_cnpjs = df[col_cnpj].dropna().unique()[:5]
            print(f"amostra de CNPJs presentes no arquivo (5 primeiros): {list(amostra_cnpjs)}")

    print("\nNenhum dos meses tentados teve dados para o fundo conhecido.")


if __name__ == "__main__":
    main()
