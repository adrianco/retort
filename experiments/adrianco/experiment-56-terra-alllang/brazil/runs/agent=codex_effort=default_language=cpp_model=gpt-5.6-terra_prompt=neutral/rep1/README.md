# Brazilian Soccer MCP

A self-contained C++17 Model Context Protocol server over stdio. It loads the six supplied Kaggle CSVs into an in-memory Brazilian soccer knowledge graph/query layer: 23k+ matches and 18k+ FIFA players.

## Build and test

```sh
cmake -S . -B build
cmake --build build -j
ctest --test-dir build --output-on-failure
```

## Run

```sh
./build/brazilian-soccer-mcp data/kaggle
```

The server accepts MCP JSON-RPC messages on standard input (newline-delimited JSON or `Content-Length` framing). Set `SOCCER_DATA_DIR` to use a different data location.

Available tools: `search_matches`, `team_statistics`, `head_to_head`, `standings`, `search_players`, and `ask_brazilian_soccer`. Team matching is accent-insensitive and tolerates common state suffixes such as `Flamengo-RJ`.

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
