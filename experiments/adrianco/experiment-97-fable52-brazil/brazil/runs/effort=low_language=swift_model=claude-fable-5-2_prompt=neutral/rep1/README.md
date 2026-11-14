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

## Implementation (Swift)

A dependency-free Swift package that loads the six CSV files into memory and serves them as an
MCP server over stdio (JSON-RPC 2.0, one message per line).

```
Package.swift
Sources/BrazilianSoccerCore/     library: CSV + dates, team normalisation, data store, queries, tools, MCP protocol
Sources/brazilian-soccer-mcp/    executable: stdio server and a one-shot --call mode
Tests/BrazilianSoccerCoreTests/  BDD-style scenarios (Given data loaded / When query / Then answer) on the real data
```

### Build, test, run

```bash
swift build -c release
swift test
.build/release/brazilian-soccer-mcp                      # MCP server on stdin/stdout
.build/release/brazilian-soccer-mcp --call standings '{"season": 2019}'   # one tool call, plain text
```

The data directory is found via `--data <dir>`, then `$BRAZILIAN_SOCCER_DATA`, then `data/kaggle`
in the working directory or one of its parents (also tried relative to the executable).

MCP client configuration:

```json
{ "mcpServers": { "brazilian-soccer": {
    "command": "/path/to/repo/.build/release/brazilian-soccer-mcp",
    "args": ["--data", "/path/to/repo/data/kaggle"] } } }
```

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, venue, competition, season, date range, round/stage ("Copa do Brasil finals", "when did X last play Y") |
| `head_to_head` | Two-club comparison: wins, draws, goals, record at each ground |
| `team_stats` | W/D/L, goals, win rate; by season, competition, home/away |
| `team_competitions` | Competitions and seasons a club appears in |
| `team_profile` | Cross-file view: match record plus FIFA squad |
| `standings` | League table calculated from results, champion and relegated clubs |
| `knockout_bracket` | Libertadores / Copa do Brasil knockout rounds with aggregates and champion |
| `compare_seasons` | Two seasons side by side |
| `league_stats` | Goals per match, home/draw/away rates, corners and shots |
| `biggest_wins` | Largest winning margins |
| `team_rankings` | Best home/away record, most goals, best defence … |
| `list_derbies` | Matches between traditional rivals |
| `search_players` | FIFA players by name, nationality, club, position, rating, age |
| `player_details` | One player's full profile and skill attributes |
| `brazilian_players_overview` | Top Brazilian players; Brazilian players per Brazilian club |
| `dataset_info` | What is loaded and known limitations |

### How the data is handled

- **Team names** are reduced to a base name plus optional state/country code, so "Palmeiras-SP",
  "Palmeiras - SP", "palmeiras" and "Sociedade Esportiva Palmeiras" are one club, while
  Atlético-MG / Athletico-PR / Atlético-GO, Botafogo-RJ / Botafogo-PB and Nacional (URU) / (PAR) stay
  separate. An unqualified name ("Botafogo") means the variant with the most matches.
- **Overlapping files** are merged: three files cover Serie A 2014-2019 and the extended-statistics file
  repeats some games. The same fixture becomes one match carrying the round from one file and corners/shots
  from another. 23,854 match rows with a result become 16,804 unique matches; every Serie A season from 2003 to 2022
  reconciles to the correct number of fixtures except 2009, where the source is one game short.
- **Dates** in ISO, ISO-with-time and DD/MM/YYYY form are all parsed to calendar days.
- Fixtures without a score (`NA`, `-`) are skipped and reported by `dataset_info`.

### Limitations worth knowing

- No file contains goal scorers, so individual top-scorer tables are not available (team scoring is).
- A champion or relegation is only declared for a complete double round-robin. The 2009 and 2023 Serie A
  seasons are incomplete in the data, so their tables are shown without a champion.
- Cup ties level on aggregate were settled by away goals or penalties, which the data does not record;
  the server says so rather than guessing (e.g. the 2015 Copa do Brasil final).
- `BR-Football-Dataset.csv` has no season or round column. Season is taken from the match date (with the
  2020 season running into early 2021), and Copa do Brasil finals are identified structurally as the last
  two-legged tie of the season.
- The `Mandante_UF`/`Visitante_UF` columns of the historical file are ignored because they are inconsistent.
- The FIFA file has squads for only 15 Brazilian clubs (not Flamengo, Palmeiras, Corinthians or São Paulo),
  and many of those players carry FIFA's generated names.
- Points deducted by sports tribunals are not in the data, so a calculated table can differ from the
  official one by those deductions.
