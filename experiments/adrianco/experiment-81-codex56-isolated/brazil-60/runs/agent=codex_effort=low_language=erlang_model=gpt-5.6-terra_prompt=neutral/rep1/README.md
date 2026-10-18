# Brazilian Soccer MCP with spec and basic data sets

## Running the server

This implementation is a dependency-free Erlang MCP server using JSON-RPC over
standard input/output. From this directory:

```sh
rebar3 compile
erl -pa _build/default/lib/brazilian_soccer_mcp/ebin -noshell -s brazilian_soccer_mcp main -s init stop
```

It loads all six CSV files at start-up and provides the `search_matches`,
`team_stats`, `head_to_head`, `standings`, `search_players`, `aggregate_stats`,
and `ask` MCP tools. Run `rebar3 eunit` for the test suite.

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
