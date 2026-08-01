# Brazilian Soccer MCP

Dependency-free Elixir MCP server and query library for the six supplied Brazilian soccer CSV datasets. It loads match results from Brasileirão, Copa do Brasil, Libertadores, extended match statistics, historical Brasileirão, plus FIFA player records.

## Run

```sh
mix escript.build
./brazilian_soccer
```

The executable speaks JSON-RPC over standard input/output using the MCP protocol. Available tools are `search_matches`, `team_statistics`, `head_to_head`, `search_players`, `standings`, and `competition_statistics`.

Library usage:

```elixir
data = BrazilianSoccer.load("data/kaggle")
BrazilianSoccer.search_matches(data, team: "Flamengo", season: 2023)
BrazilianSoccer.team_statistics(data, "Corinthians", season: 2022, venue: :home)
BrazilianSoccer.head_to_head(data, "Palmeiras", "Santos")
BrazilianSoccer.search_players(data, nationality: "Brazil", min_overall: 80)
BrazilianSoccer.standings(data, 2019, competition: "Brasileirão")
```

Team searches ignore accent, case, and trailing state variants such as `Palmeiras-SP`; dates accept ISO/datetime and Brazilian `DD/MM/YYYY` forms. Incomplete scheduled matches remain searchable but do not affect calculated records or standings.

## Tests

```sh
mix test
```

The test suite includes Given/When/Then-style coverage for name/date normalization, match lookup, head-to-head records, team statistics, standings, player search, and loading all supplied datasets.

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
