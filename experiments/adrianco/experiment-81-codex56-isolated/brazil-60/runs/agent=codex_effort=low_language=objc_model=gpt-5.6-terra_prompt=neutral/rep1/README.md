# Brazilian Soccer MCP with spec and basic data sets

## Running the MCP server

Build and start the stdio MCP server from this directory:

```sh
make
./brazilian-soccer-mcp
```

It implements `initialize`, `tools/list`, and `tools/call` using newline-delimited
JSON-RPC on standard input/output.  `mcp.json` is the ready-to-use client entrypoint.
The `standings` tool accepts the distinct competition values `Brasileirão`,
`Brasileirão Historical`, `Copa do Brasil`, and `Libertadores`; the first is the
canonical Série A source and is intentionally not combined with the historical CSV.

## Specification
brazilian-soccer-mcp-guide.md

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv
