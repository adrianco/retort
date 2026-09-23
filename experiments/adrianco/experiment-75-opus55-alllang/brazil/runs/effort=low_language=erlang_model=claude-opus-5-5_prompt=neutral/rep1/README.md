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

## Erlang MCP server

Requires Erlang/OTP 27+ (uses the built-in `json` module) and rebar3.

```sh
rebar3 eunit          # run the BDD-style test suite (43 tests)
rebar3 escriptize     # build _build/default/bin/brsoccer
```

Run it as a stdio MCP server (newline-delimited JSON-RPC 2.0), e.g. in a Claude/MCP client config:

```json
{"mcpServers": {"brazilian-soccer": {"command": "/path/to/_build/default/bin/brsoccer",
                                     "env": {"BRSOCCER_DATA": "/path/to/data/kaggle"}}}}
```

`BRSOCCER_DATA` is optional; by default `data/kaggle` is searched for from the current directory upward.

Tools: `search_matches`, `head_to_head`, `team_stats`, `standings`, `league_stats`, `biggest_wins`,
`best_records`, `top_scoring_teams`, `derbies`, `team_competitions`, `search_players`,
`brazilian_clubs_players`, `dataset_info`.

Modules: `brsoccer_csv` (CSV parsing), `brsoccer_norm` (team name / date normalization),
`brsoccer_data` (loads all 6 files, de-duplicates fixtures across sources), `brsoccer_query`
(query engine), `brsoccer_tools` (MCP tool schemas + text formatting), `brsoccer` (stdio server).

Data notes: the FIFA 19 data has no Flamengo, Palmeiras, Corinthians or São Paulo squads. The 2023
Brasileirão comes only from BR-Football-Dataset, which is missing some fixtures, so the computed
2023 table is incomplete.
