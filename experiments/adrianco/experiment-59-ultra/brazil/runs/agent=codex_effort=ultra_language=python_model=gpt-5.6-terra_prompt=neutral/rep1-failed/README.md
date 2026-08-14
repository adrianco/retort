# Brazilian Soccer MCP Server

A dependency-free Python MCP server for querying the six bundled Brazilian soccer CSV datasets. It provides structured match, player, team, standings, and aggregate-statistics tools, plus a deterministic convenience tool for common natural-language football questions.

## Run it

The server uses the MCP stdio transport: newline-delimited JSON-RPC messages on standard input and output.

```bash
python3 mcp_server.py
```

It implements `initialize`, `ping`, `tools/list`, and `tools/call`. Its tools are:

- `ask_soccer` — deterministic handling for common natural-language questions and score follow-ups
- `search_matches` — filter by team, opponent, home/away side, date range, competition, season, stage/round, and source
- `team_statistics` and `head_to_head` — wins, draws, losses, goals, points, win rate, and direct meetings
- `search_players` — FIFA player name, nationality, club, position, and rating filters
- `competition_standings`, `team_leaderboard`, and `analyze_statistics` — tables, leaders, goals-per-match, home-win rate, biggest wins, and away records
- `competition_matches_by_stage`, `team_profile`, and `dataset_summary` — stage results, cross-file club views, and source/provenance coverage
- `knowledge_graph` — explicit team, match, competition, player, and club nodes with source-derived relationship edges

The default query path avoids double counting overlaps between the three match datasets. For each competition and season it uses the dedicated source first, then historical data, then the extended-statistics source. Pass a `source` value to inspect an individual CSV directly.

Team matching is accent-insensitive and understands common variants such as `São Paulo`, `Sao Paulo-SP`, and `Sport Club Corinthians Paulista`, while retaining meaningful state distinctions such as `Botafogo-RJ` versus `Botafogo-PB`. Unknown player names are returned as an empty result rather than inferred or invented.

## Test

```bash
python3 -m pytest -q
```

The BDD-style test suite verifies all six data sources, multiple date formats, team normalization, incomplete-score handling, standings, player filters, 20 natural-language scenarios, MCP JSON-RPC behavior, and the requested lookup/aggregate performance budgets.

## Specification

`TASK.md` is the task specification. `brazilian-soccer-mcp-guide.md` is the original project guide.

## Data sources

Kaggle data cannot be downloaded without an account, so these freely available datasets have been pre-downloaded for use here:

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
