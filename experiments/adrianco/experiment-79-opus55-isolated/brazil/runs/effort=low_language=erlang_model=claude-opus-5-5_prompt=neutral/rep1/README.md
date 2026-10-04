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

An MCP server written in Erlang/OTP (27 or newer, for the built-in `json` module) with no
external dependencies. It speaks JSON-RPC 2.0 over stdio (one message per line), loads the
six CSV files into memory at start-up (about 4 s) and exposes 15 tools.

### Build, test, run

```sh
rebar3 eunit          # unit, BDD scenario and MCP protocol tests against the real data
rebar3 escriptize     # builds _build/default/bin/brsoccer_mcp
./_build/default/bin/brsoccer_mcp
```

The data directory is `$BRSOCCER_DATA_DIR`, else `data/kaggle` under the current directory,
else `data/kaggle` relative to the built escript. Example client configuration:

```json
{"mcpServers": {"brazilian-soccer": {"command": "/path/to/repo/_build/default/bin/brsoccer_mcp"}}}
```

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | matches by team, opponent, venue, competition, season, date range, round, stage (e.g. Copa do Brasil finals) |
| `head_to_head` | record and recent meetings of two teams |
| `team_stats` | W/D/L, goals, win rate; optional season, competition, home/away |
| `standings` | league table calculated from results, with champion and relegation zone |
| `season_summary` | goals per match, home/draw/away rates, per-season breakdown |
| `compare_seasons` | two seasons side by side |
| `biggest_wins` | largest winning margins |
| `team_rankings` | best home/away/overall record, most goals, best defence, most wins |
| `team_competitions` | competitions and seasons a team appears in |
| `derbies` | matches between traditional rivals |
| `search_players` | FIFA players by name, nationality, club, position, rating, age |
| `player_details` | full profile of one player |
| `club_player_summary` | players of a nationality grouped by club |
| `team_profile` | cross-file: match record per competition plus FIFA squad |
| `data_summary` | loaded files, competitions and season coverage |

### Source layout

| File | Role |
|------|------|
| `src/bs_csv.erl` | CSV parser (quotes, BOM, CRLF) |
| `src/bs_team.erl` | team-name normalisation, club alias table, rivalries |
| `src/bs_data.erl` | loading, date parsing, merging of overlapping files |
| `src/bs_query.erl` | filters and aggregations |
| `src/bs_tools.erl` | tool schemas, argument validation, text rendering |
| `src/bs_mcp.erl` | MCP / JSON-RPC handling |
| `src/brsoccer.erl` | stdio entry point |
| `test/` | eunit suites: `bs_unit_tests`, `bs_scenarios_tests` (Given/When/Then), `bs_mcp_tests` |

### Data handling notes

- **Team names** are reduced to one key per club: accents/case folded, state or country suffix
  split off (`Palmeiras-SP`, `Palmeiras - SP`, `America MG`, `Nacional (URU)`), affixes such as
  `EC`/`FC` removed, and common clubs mapped through an alias table. Homonyms from other states
  (`Flamengo - PI`, `Atlético-GO`) stay separate.
- **Overlapping files**: three files contain Serie A seasons. Queries use a merged view in which
  a match with the same competition and teams within two days counts once (23,954 rows become
  about 16,800 matches). Rows with a score win over unplayed fixtures.
- **Known data limits**, reported by the tools rather than hidden: the 2023 Serie A data has 377
  of 380 matches, so that table is labelled incomplete; the FIFA file has no players for
  Flamengo, Palmeiras, Corinthians, São Paulo and some other Brazilian clubs; goal scorers are
  not in any file, so "top scorers" are available per team only.
- Relegation is shown as the bottom four of a complete 20-team Serie A season.
