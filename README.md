# Análise de Fundos Multimercados

Projeto Python para analisar fundos multimercados brasileiros: baixa dados
públicos da CVM, aceita carteiras próprias (CSV/Excel), calcula métricas de
risco/retorno e compara com benchmarks (CDI, IPCA).

## Estrutura

```
src/fundos/
  catalogo.py     # carrega o universo de fundos do estudo (data/catalogo_fundos_multimercados.xlsx)
  cvm.py          # download/parse de dados públicos da CVM (cadastro, informe diário, série histórica)
  master.py       # identifica o fundo master de cada feeder via CDA (composição da carteira) da CVM
  benchmarks.py   # séries de CDI e IPCA via API do Banco Central (SGS)
  loaders.py      # leitura de planilhas próprias (CSV/XLSX) de cotas de fundos
  metrics.py       # retorno, volatilidade, Sharpe, drawdown, correlação
scripts/
  estudo_masters.py  # identifica os masters do catálogo e calcula o retorno de cada um desde o início
notebooks/         # exploração interativa
  01_exploracao.ipynb    # fluxo geral: CVM -> métricas -> comparação com CDI
  02_catalogo_btg.ipynb  # rankings do catálogo + cruzamento com CVM para o top N
examples/           # modelo de planilha para carteira própria
tests/               # testes das funções de métricas e carregamento
data/
  catalogo_fundos_multimercados.xlsx  # universo de 27 fundos multimercados do estudo (versionado)
  raw/           # cache de dados baixados da CVM/BCB (não versionado)
  processed/     # saídas processadas: masters.csv, retorno_historico_masters.csv, series_masters.csv (não versionado)
```

## Universo do estudo

`data/catalogo_fundos_multimercados.xlsx` traz os 27 fundos multimercados que
usamos como base da análise (CNPJ, gestora, classificação Anbima/CVM, taxas e
métricas de performance de 12/24/36 meses já calculadas pela distribuidora).

```python
from fundos.catalogo import carregar_catalogo, ranking, resumo_por_gestora

catalogo = carregar_catalogo()
ranking(catalogo, "sharpe_12m", top_n=10)        # melhores Sharpe 12M
ranking(catalogo, "volatilidade_12m", ascendente=True)  # menos voláteis
resumo_por_gestora(catalogo)                      # patrimônio/retorno por gestora
```

Os CNPJs do catálogo servem de ponte para os dados diários da CVM
(`fundos.cvm`), permitindo recalcular as métricas de forma independente e
analisar séries históricas completas — veja `notebooks/02_catalogo_btg.ipynb`.

> `fundos.cvm` e `fundos.benchmarks` precisam de acesso a `dados.cvm.gov.br`
> e `api.bcb.gov.br`. Em ambientes com rede restrita (sandboxes, alguns CI)
> essas chamadas podem falhar — rode localmente ou em CI com rede liberada.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Fontes de dados

### 1. CVM (dados públicos, automático)

A CVM publica diariamente as cotas de todos os fundos registrados no Brasil.

```python
from fundos.cvm import fetch_cadastro, fetch_informe_diario, filtrar_multimercados, cotas_do_fundo

cadastro = fetch_cadastro()                       # cadastro completo de fundos (CNPJ, nome, classe...)
multimercados = filtrar_multimercados(cadastro)    # apenas fundos classe "Fundo Multimercado"

informe = fetch_informe_diario("2026-07")           # cotas diárias de TODOS os fundos em jul/2026
cotas_fundo = cotas_do_fundo(informe, "00.000.000/0001-00")
```

Os arquivos baixados ficam em cache local (`data/raw/`) para não re-baixar a
cada execução. Para séries longas (vários anos), use
`fetch_serie_historica(cnpj, data_inicio)` em vez de `fetch_informe_diario` +
`cotas_do_fundo` — ela filtra por CNPJ mês a mês em vez de carregar o universo
inteiro de fundos de cada mês em memória.

### 2. Planilhas próprias

Se você já tem os dados de cota/data de um fundo (ex: extrato do seu banco),
use o modelo em `examples/minha_carteira.csv`:

```csv
data,fundo,valor_cota
2026-01-02,Meu Fundo XP,1.523891
2026-01-03,Meu Fundo XP,1.524012
...
```

```python
from fundos.loaders import carregar_carteira

carteira = carregar_carteira("examples/minha_carteira.csv")
```

`carregar_carteira` também aceita `.xlsx` e reconhece variações comuns de
nome de coluna (Data/DT_COMPTC, Cota/Valor da Cota/VL_QUOTA, Fundo/Nome).

## Métricas

```python
from fundos.metrics import (
    retornos_diarios, retorno_acumulado, retorno_anualizado,
    volatilidade_anualizada, indice_sharpe, max_drawdown, matriz_correlacao,
)

retornos = retornos_diarios(cotas_fundo.set_index("DT_COMPTC")["VL_QUOTA"])
print("Retorno anualizado:", retorno_anualizado(retornos))
print("Volatilidade anualizada:", volatilidade_anualizada(retornos))
print("Max drawdown:", max_drawdown(retorno_acumulado(retornos)))
```

## Benchmarks (CDI / IPCA)

```python
from fundos.benchmarks import cdi_diario, ipca_mensal

cdi = cdi_diario("2026-01-01", "2026-07-31")
ipca = ipca_mensal("2026-01-01", "2026-07-31")
```

Use o CDI diário como taxa livre de risco no `indice_sharpe(retornos, cdi)`.

## Fundo master e histórico desde o início

A maioria dos 27 fundos do catálogo é um **feeder** (FIC — Fundo de
Investimento em Cotas): aplica quase 100% do patrimônio num único fundo
**master**, que é quem de fato executa a estratégia. Para estudar o
histórico real de cada estratégia (não só os últimos 12-36 meses que o
catálogo já traz), é o master que precisa ser analisado, desde o início dele
— que costuma ser bem anterior ao início do feeder correspondente.

`fundos.master` identifica o master de cada feeder lendo a **Composição da
Carteira (CDA)** que a CVM publica mensalmente: para cada fundo, olha o
bloco "cotas de fundos" e escolhe a posição de maior valor de mercado.

```bash
python scripts/estudo_masters.py
```

O script:
1. Para cada um dos 27 fundos, identifica o CNPJ do master via CDA (últimos
   6 meses disponíveis, já que a CVM publica a CDA com 1-2 meses de atraso)
   → `data/processed/masters.csv`.
2. Baixa a série completa de cotas de cada master desde 2000 até hoje e usa a
   primeira cota que existir como data de início real (não confiamos na data
   de início do cadastro da CVM — os masters por trás dos FICs nem sempre
   aparecem em `cad_fi.csv` com o mesmo CNPJ, provavelmente por causa da
   reforma de fundos estruturados em classes). Calcula retorno total, retorno
   anualizado, volatilidade, Sharpe (vs. CDI) e max drawdown →
   `data/processed/retorno_historico_masters.csv`.
3. Salva a série diária de retorno acumulado de cada master →
   `data/processed/series_masters.csv` (para plotar depois).

Roda localmente ou em CI com rede liberada (ver aviso acima). Na primeira
execução busca ~300 arquivos mensais (2000 até hoje) — demora, mas cada mês é
baixado uma única vez e reaproveitado por todos os 27 fundos (cache em
`data/raw/`); reexecuções são rápidas.

> A CVM já mudou nomes de coluna (`CNPJ_FUNDO` → `CNPJ_FUNDO_CLASSE`) e o
> layout de alguns arquivos ao longo dos anos. `fundos.cvm` e `fundos.master`
> detectam a coluna certa dinamicamente, mas se a CVM mudar de novo e o
> script falhar com `KeyError`/`FileNotFoundError`, confira a listagem atual
> em `dados.cvm.gov.br/dados/FI/DOC/` e ajuste as constantes no topo de
> `cvm.py`/`master.py`.

## Notebook de exemplo

`notebooks/01_exploracao.ipynb` mostra o fluxo completo: buscar fundos
multimercados na CVM, baixar as cotas de um período, calcular as métricas e
comparar com o CDI.

## Testes

```bash
pytest
```
