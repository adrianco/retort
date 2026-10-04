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

## Implementation (Elixir)

A dependency-free Elixir MCP server (stdio, newline-delimited JSON-RPC 2.0) over the six CSV files.
Requires Elixir 1.18+ (uses the built-in `JSON` module).

```bash
mix test                      # 62 BDD-style ExUnit tests, run against the real data
mix soccer.mcp                # run the server (data dir: $BRAZILIAN_SOCCER_DATA_DIR or ./data/kaggle)
mix escript.build && ./brazilian_soccer_mcp [DATA_DIR]
```

MCP client configuration example:

```json
{"mcpServers": {"brazilian-soccer": {"command": "/path/to/brazilian_soccer_mcp", "args": ["/path/to/data/kaggle"]}}}
```

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | matches by team, opponent, venue, competition, season, date range, round, stage |
| `head_to_head` | two-team comparison with meetings list |
| `team_stats` | W/D/L, goals, win rate — overall, home, away, per competition |
| `team_profile` | cross-file: competitions, record, recent results and FIFA squad |
| `standings` | season table calculated from results; champion and relegated teams |
| `team_rankings` | best home/away record, most goals, etc. |
| `competition_stats` | goals per match, home/draw/away rates |
| `compare_seasons` | two seasons side by side |
| `biggest_wins` | largest margins / highest-scoring matches |
| `derbies` | matches between traditional rivals |
| `search_players`, `player_details`, `players_by_club` | FIFA player database |
| `dataset_info` | loaded files and coverage |

### Layout

- `lib/brazilian_soccer/csv.ex` – RFC 4180 CSV parser (quotes, BOM, CRLF)
- `lib/brazilian_soccer/teams.ex` – team name normalisation (state suffixes, accents, aliases, derbies)
- `lib/brazilian_soccer/loader.ex` – loads the files into one match list; fixtures present in several files are merged
- `lib/brazilian_soccer/queries.ex`, `players.ex` – query and statistics functions
- `lib/brazilian_soccer/mcp/` – tool definitions and the JSON-RPC server

### Data notes

- Fixtures that appear in more than one file (same competition and teams, within two days) are merged so statistics are not double counted; 22,953 dated rows become 16,803 matches.
- `BR-Football-Dataset.csv` has no season column; the season is the calendar year, except early-2021 matches that belong to the delayed 2020 season.
- The UF columns of `novo_campeonato_brasileiro.csv` are wrong for some clubs (Bahia as "BH", Vitória as "ES") and are ignored for well-known clubs.
- The FIFA file does not contain every Brazilian club (no Flamengo, Corinthians, Palmeiras or São Paulo), and its Brazilian-league player names are FIFA's generic ones.
- Série A 2023 is three matches short in the data, so its table is reported as incomplete with no champion.
