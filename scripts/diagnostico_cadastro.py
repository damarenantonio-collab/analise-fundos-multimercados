#!/usr/bin/env python3
"""Diagnóstico: baixa o cadastro da CVM e mostra as colunas reais + o registro
de um fundo master conhecido, pra descobrir o nome certo da coluna de data de
início de atividade (usada por `data_inicio_atividade`).

    python scripts/diagnostico_cadastro.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from fundos.cvm import coluna_cnpj_fundo, fetch_cadastro  # noqa: E402

# Kapitalo Master II, que apareceu no log do estudo_masters.py
CNPJ_CONHECIDO = "12.083.748/0001-84"

pd.set_option("display.max_rows", None)


def main() -> None:
    print("Baixando cadastro da CVM...")
    cadastro = fetch_cadastro()
    print(f"shape={cadastro.shape}")
    print(f"colunas ({len(cadastro.columns)}): {list(cadastro.columns)}")

    coluna_cnpj = coluna_cnpj_fundo(cadastro)
    print(f"\ncoluna de CNPJ usada: {coluna_cnpj}")

    linha = cadastro[cadastro[coluna_cnpj] == CNPJ_CONHECIDO]
    print(f"linhas para {CNPJ_CONHECIDO}: {len(linha)}")
    if linha.empty:
        amostra = cadastro[coluna_cnpj].dropna().unique()[:5]
        print(f"CNPJ não encontrado. Amostra de CNPJs presentes: {list(amostra)}")
        return

    print("\nTodos os campos do registro encontrado:")
    print(linha.iloc[0].to_string())

    print("\nColunas que parecem ser de data (nome contém 'DT' ou 'DATA'):")
    colunas_data = [c for c in cadastro.columns if "DT" in c.upper() or "DATA" in c.upper()]
    print(colunas_data)


if __name__ == "__main__":
    main()
