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

## Implementation

A dependency-free Python (3.10+) MCP server, `brazilian_soccer_mcp`, that answers questions about
Brazilian football from all six provided datasets. It speaks MCP over stdio (JSON-RPC 2.0:
`initialize`, `ping`, `tools/list`, `tools/call`). Every tool returns readable text plus the same
answer as `structuredContent`.

### Running

```bash
python -m brazilian_soccer_mcp            # serves on stdio, reads data/kaggle
SOCCER_DATA_DIR=/path/to/csvs python -m brazilian_soccer_mcp
```

Example MCP host configuration (e.g. Claude Desktop / Claude Code):

```json
{"mcpServers": {"brazilian-soccer": {"command": "python", "args": ["-m", "brazilian_soccer_mcp"],
                                     "cwd": "/path/to/this/repo"}}}
```

### Tools

| Tool | Answers |
|------|---------|
| `find_matches` | matches by team, opponent, home/away, competition, season, date range, stage (+ head-to-head) |
| `head_to_head` | wins/draws/goals between two teams and recent meetings |
| `team_record` | W/D/L, goals, points, win rate — by season, competition, home/away |
| `team_competitions` | which competitions and seasons a team played |
| `team_profile` | record + recent results + FIFA squad (cross-file) |
| `standings` | league table from results, champion, bottom-four relegation |
| `cup_finals` | Copa do Brasil / Libertadores finals with aggregate and winner |
| `knockout_bracket` | knockout ties by stage, with who went through |
| `find_derbies` | Fla-Flu, Grenal, Derby Paulista, Clássico Mineiro, Ba-Vi and other rivalries |
| `competition_stats` | goals per match, home/draw/away rates |
| `biggest_wins` | largest winning margins |
| `rank_teams` | best home/away/overall win rate, most goals scored/conceded, points, wins |
| `compare_seasons` | season-by-season stats, champion, relegated, top-scoring team |
| `search_players` / `player_profile` | FIFA players by name, nationality, club, position, rating |
| `brazilian_club_players` | players at clubs that appear in the Brazilian match data (cross-file) |
| `dataset_info` | files loaded, row counts, competitions and seasons covered |

### Data handling

- **Team names** are normalised across datasets (`Palmeiras-SP`, `Palmeiras - SP`, `Sociedade Esportiva
  Palmeiras`, `Sao Paulo`/`São Paulo`, `EC Bahia`). Clubs sharing a short name in different states
  (Atlético-MG/PR/GO, Botafogo-RJ/SP/PB), and foreign namesakes (Guaraní (PAR)), stay separate.
- **Dates**: ISO, ISO with time, and Brazilian `DD/MM/YYYY`.
- **Overlapping files** are merged, not double counted. The priority order is `Brasileirao_Matches` >
  `novo_campeonato_brasileiro` > cup files > `BR-Football-Dataset`, and later copies only add
  corners/shots/attacks. Every Série A season 2006–2022 has exactly 380 matches, except 2016 (379: one
  fixture was never played).

### Tests: Acceptance Test-Driven Development

The tests follow Dave Farley's four-layer model:

1. **Specifications**: `tests/acceptance/test_*.py`, in football language (`given.brasileirao_match(...)`,
   `teams.record(team="Corinthians", venue="home")`, `teams.confirm_record(wins=1, ...)`).
2. **DSL**: `tests/acceptance/dsl/`, with defaults and sequence-generated dates.
3. **Protocol drivers**: `tests/acceptance/drivers/`. One writes synthetic data in each Kaggle file's
   native format. The other launches the real server as a subprocess and talks MCP over stdio.
4. **System under test**: `brazilian_soccer_mcp/`.

Each spec builds its own synthetic dataset and runs its own server process, so the specs are isolated
from each other. `test_provided_datasets.py` runs against the real files: real outcomes (2019 champion
Flamengo 90 pts, 2020 relegation, 2020 Copa do Brasil), the < 2 s / < 5 s response times, and 24 sample
questions. Unit tests sit in `tests/unit/`.

```bash
python -m pytest            # 120 tests, ~2 s
```
