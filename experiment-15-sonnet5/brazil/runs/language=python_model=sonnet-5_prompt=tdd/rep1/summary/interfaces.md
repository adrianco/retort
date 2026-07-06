# Interfaces

## MCP tools (`server.py`, via `FastMCP("brazilian-soccer")`)

| Tool | Parameters | Returns | Backing query |
|------|-----------|---------|---------------|
| `find_matches` | team, opponent?, competition?, season? | text list of matches | `queries.find_matches` |
| `head_to_head` | team_a, team_b, competition?, season? | H2H W/L/D record + match lines | `queries.head_to_head` |
| `team_record` | team, competition?, season?, venue? | matches/W/D/L/GF/GA/win-rate | `queries.team_record` |
| `standings` | competition="Brasileirao", season? | ranked table with points | `queries.standings` |
| `biggest_wins` | competition?, season?, n=10 | top matches by goal margin | `queries.biggest_wins` |
| `average_goals_per_match` | competition?, season? | avg goals float | `queries.average_goals_per_match` |
| `home_win_rate` | competition?, season? | home win % | `queries.home_win_rate` |
| `search_players` | name?, nationality?, club?, position? | player rows with ratings | `queries.search_players` |
| `top_players` | n=10, nationality?, club? | ranked players by overall | `queries.top_players` |

## Data schema (unified matches frame — `MATCH_COLUMNS`)

`date`, `season`, `round`, `stage`, `competition`, `source`, `home_team_raw`, `away_team_raw`, `home_team` (canonical key), `away_team` (canonical key), `home_team_display`, `away_team_display`, `home_goal`, `away_goal`.

Sources unified: `Brasileirao_Matches.csv` (Brasileirao), `Brazilian_Cup_Matches.csv` (Copa do Brasil), `Libertadores_Matches.csv` (Copa Libertadores), `BR-Football-Dataset.csv` (tournament column), `novo_campeonato_brasileiro.csv` (pre-2012 only, to avoid double-counting). Players: `fifa_data.csv` (renamed columns + `club_key`).

## HTTP routes / CLI commands

(none — the interface is the MCP tool set; `python -m brazilian_soccer_mcp.server` starts the stdio server via `mcp.run()`.)
