# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Clojure implementation

Requires `clojure` CLI (tools.deps).

Run tests:
```
clojure -X:test
```

Run the MCP stdio server:
```
clojure -M:mcp
```

Source layout:
- `src/soccer/data.clj` — CSV loaders + team/date normalization
- `src/soccer/query.clj` — match/team/player/competition query functions
- `src/soccer/mcp.clj` — minimal JSON-RPC MCP server over stdio
- `test/soccer/` — clojure.test suites

Exposed MCP tools: `list_matches_between`, `team_matches`, `team_record`,
`head_to_head`, `standings`, `search_players`, `top_players`, `biggest_wins`,
`statistics`.

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
