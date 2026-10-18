# Interfaces

## MCP tools (JSON-RPC `tools/call`)

| Tool | Arguments | Returns | Handler |
|------|-----------|---------|---------|
| search_matches | team / home_team / away_team / season / competition / from / to / limit | matches (date-desc, limited) | `soccer_query:find_matches/2` |
| team_stats | team, venue?, season?/competition? | W/D/L, goals for/against, win_rate | `soccer_query:team_stats/2` |
| head_to_head | team_a, team_b | per-team wins, draws, match list | `soccer_query:head_to_head/3` |
| standings | competition, season | ranked table (points, GD, GF) computed from matches | `soccer_query:standings/3` |
| search_players | name / nationality / club / position / limit | players sorted by overall | `soccer_query:search_players/2` |
| aggregate_stats | (match filters) | matches, total_goals, goals_per_match, home_win_rate | `soccer_query:aggregate/2` |
| ask | question | NL convenience → routes "compare A and B" to head_to_head | `soccer_query:answer/2` |

Transport: JSON-RPC 2.0 over stdin/stdout (`soccer_mcp:loop/1`), `initialize` + `tools/list` + `tools/call`. `protocolVersion` reported as `2024-11-05`.

## Data schema (normalized match map)

`date`, `date_sort` (int YYYYMMDD), `season`, `competition`, `home`, `away`, `home_normalized`, `away_normalized`, `home_goals`, `away_goals`, `round`, `stage`, `source`, `raw`.

Player map: `id`, `name`, `age`, `nationality`, `overall`, `potential`, `club`, `position`, `jersey_number`.

## Data sources loaded (`soccer_data:load/1`)

Brasileirao, Copa do Brasil (Brazilian_Cup), Libertadores, BR-Football-Dataset (extended), novo_campeonato_brasileiro (historical), fifa_data (players). Per-dataset column mapping handles the differing CSV headers.
