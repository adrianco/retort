# Brazilian Soccer MCP with spec and basic data sets

## Running the server

This repository contains a dependency-free MCP server that reads all six local
CSV files and serves JSON-RPC over standard input/output:

```bash
python3 server.py
```

The server exposes `search_matches`, `team_statistics`, `head_to_head`,
`get_standings`, `search_players`, and `aggregate_statistics`. Team comparisons
are case-, accent-, and state-suffix-insensitive (for example, `São Paulo-SP`
matches `Sao Paulo`). Results include structured JSON and textual JSON content
as required by MCP tool calls.

Run the BDD-style test suite with:

```bash
python3 -m pytest -q
```

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
