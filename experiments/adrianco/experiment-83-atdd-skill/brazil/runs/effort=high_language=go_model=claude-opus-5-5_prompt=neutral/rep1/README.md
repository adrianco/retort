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

## Implementation (Go)

A dependency-free Go MCP server (`brsoccer`) that loads all six CSV files into
memory at startup (~0.1-0.4 s) and answers questions through MCP tools over
stdio (JSON-RPC 2.0, protocol versions 2024-11-05 / 2025-03-26 / 2025-06-18).

### Build, test, run

```sh
go build -o brsoccer .
go test ./...                       # data, normalisation, 33 sample questions, MCP protocol
./brsoccer                          # serve MCP on stdin/stdout (logs to stderr)
./brsoccer tools                    # list tools
./brsoccer call standings '{"season":2019,"limit":5}'   # run a tool from the shell
```

The data directory defaults to `$BRSOCCER_DATA`, then `./data/kaggle`, then
`data/kaggle` next to the binary; override with `-data DIR`.

Claude Desktop / Claude Code configuration:

```json
{ "mcpServers": { "brazilian-soccer": {
    "command": "/abs/path/brsoccer",
    "args": ["-data", "/abs/path/data/kaggle"] } } }
```

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | matches by team / opponent / home / away / competition / season / date range / stage / derbies, with head-to-head summary |
| `head_to_head` | W/D/L, goals, per-competition split, recent and biggest results between two teams |
| `team_record` | record for a team, optionally by season, competition and home/away, plus league finish |
| `team_overview` | competitions played, league finishes, inferred titles and FIFA squad (cross-file) |
| `standings` | league table computed from results, champion and relegated teams |
| `rank_teams` | rank teams by points, wins, win rate, goals for/against, goal difference… (home/away aware) |
| `biggest_wins` | largest victory margins by competition / season / team |
| `competition_stats` | goals per match, home/draw/away rates, corners & shots, season comparison table |
| `knockout_bracket` | Libertadores / Copa do Brasil ties with aggregate scores and winners |
| `search_players`, `player_profile`, `club_squads` | FIFA 19 player search, profiles, players per club |
| `find_team`, `dataset_info` | name resolution diagnostics, data coverage and derby list |

### Data handling

- **Team names** (`normalize.go`): accents folded, state/country suffixes
  (`-SP`, ` - SP`, ` SP`, `(URU)`) split off, club-type noise (`EC`, `FC`…)
  removed, and a table of major clubs maps aliases (`Athletico Paranaense`,
  `Atlético-PR`, `Athletico`) to one team while keeping same-named clubs from
  different states apart (Botafogo-RJ/SP/PB, Atlético-MG/PR/GO, América-MG/RN).
- **De-duplication** (`data.go`): Série A games appear in up to three files and
  Copa do Brasil games in two; they are merged (same teams, kick-off within
  36 h), keeping round, stage, arena and shot/corner stats from every source.
  Each complete Série A season 2006-2022 yields exactly 380 games; computed
  champions match the real ones (e.g. Flamengo 90 pts in 2019).
- **Dates**: `YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS` and `DD/MM/YYYY`. The COVID-
  delayed 2020 season (finished Feb 2021) is assigned correctly.
- **Known data limits**: FIFA 19 lacks Flamengo, Palmeiras, Corinthians and
  São Paulo (the tools say so); Série A 2023 has 377 of 380 games; unplayed
  fixtures (`NA`) are skipped; penalty shoot-outs are not recorded.
