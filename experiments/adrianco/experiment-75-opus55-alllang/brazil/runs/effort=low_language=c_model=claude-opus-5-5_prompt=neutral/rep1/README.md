# Brazilian Soccer MCP with spec and basic data sets

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

## C implementation

A dependency-free C11 MCP server (JSON-RPC 2.0 over stdio, one message per line).

```
make            # builds ./soccer-mcp and ./test_soccer
make test       # runs the BDD-style test suite against data/kaggle
./soccer-mcp [data_dir]   # or SOCCER_DATA_DIR=...; defaults to data/kaggle
```

Claude Code registration: `claude mcp add brazilian-soccer -- /abs/path/soccer-mcp /abs/path/data/kaggle`

Tools: `search_matches`, `head_to_head`, `team_stats`, `standings`, `search_players`,
`players_by_brazilian_club`, `biggest_wins`, `competition_stats`, `best_records`,
`team_competitions`, `derbies`, `compare_seasons`.

Layout: `src/data.c` (CSV loading, team-name/date normalization, cross-file de-duplication),
`src/query.c` (queries), `src/mcp.c` (JSON parser + MCP protocol), `src/main.c`, `tests/test_soccer.c`.
