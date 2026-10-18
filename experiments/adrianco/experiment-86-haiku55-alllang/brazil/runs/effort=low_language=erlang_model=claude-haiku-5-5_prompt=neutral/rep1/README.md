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

## Implementation (Erlang)

An MCP server (JSON-RPC 2.0 over stdio) that answers structured queries over the
six CSV files in `data/kaggle/`. Built with OTP 27+ (uses the built-in `json`
module) and no third-party dependencies.

### Layout
- `src/soccer_csv.erl` – RFC 4180 CSV parser (BOM, CRLF, quoted fields)
- `src/soccer_util.erl` – team-name cleanup, accent-insensitive tokens, date and number parsing
- `src/soccer_teams.erl` – club alias table (e.g. "Atletico Mineiro" = "Atletico-MG")
- `src/soccer_loader.erl` – loads all six files, dedupes matches shared between files, labels Copa do Brasil finals
- `src/soccer_stats.erl` – pure queries: match search, records, standings, league summary, biggest wins, player search, club summary
- `src/soccer_tools.erl` – MCP tool definitions and text formatting
- `src/soccer_mcp.erl` – JSON-RPC handling and the stdio loop
- `test/` – EUnit tests in Given/When/Then comment style (`soccer_data_tests` runs against the real CSVs)

### Build, test, run
```
rebar3 eunit                 # run the tests
rebar3 escriptize            # builds _build/default/bin/soccer_mcp
SOCCER_DATA_DIR=data/kaggle ./_build/default/bin/soccer_mcp   # speaks MCP on stdin/stdout
```

### Tools
`search_matches`, `team_record`, `head_to_head`, `standings`, `league_summary`,
`biggest_wins`, `search_players`, `club_summary`. The MCP client's LLM turns
the natural-language question into these structured arguments.

### Known data limits
- Team names are matched on tokens, so `Atletico` matches both Atlético-MG and Athletico-PR. Use the full name to be specific.
- The Brasileirão matches overlap between files (2012–2019); duplicates are removed by season, competition, ordered teams and score.
- Copa do Brasil finals are the two-legged final round per season. For 2021 the data has no clear two-legged final, so no final is labelled.
- The FIFA dataset has no "Gabriel Barbosa"; `search_players` returns no match for him.
