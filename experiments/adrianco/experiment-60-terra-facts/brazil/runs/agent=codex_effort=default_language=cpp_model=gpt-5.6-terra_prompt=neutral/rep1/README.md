# Brazilian Soccer MCP

A dependency-free C++17 stdio [Model Context Protocol](https://modelcontextprotocol.io) server over the six supplied Brazilian soccer CSV datasets. It loads all five match sources and the FIFA player database at start-up, normalizes club-name spelling/state suffixes and accents, and exposes structured query tools to an LLM.

## Build and test

```sh
cmake -S . -B build
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

## Run

```sh
./build/brazilian_soccer_mcp data/kaggle
```

The server uses newline-delimited JSON-RPC over standard input/output. Set `BRAZILIAN_SOCCER_DATA` to override the data directory. It implements MCP `initialize`, `tools/list`, and `tools/call`; clients should launch it with the repository root as their working directory or pass the data directory explicitly.

Available tools:

- `search_matches` — team/opponent, competition, season, and date range filters across all match files.
- `team_statistics` — overall/home/away win-loss-draw and goal totals.
- `head_to_head` — team comparison and result counts.
- `standings` — points table calculated from supplied results.
- `search_players` — player name, nationality, club, and position filters, sorted by rating.

The test executable covers loading all datasets, normalized variants such as `São Paulo-SP`, match and player discovery, records, head-to-head accounting, and standings.

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
