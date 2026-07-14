# Interfaces

## Transport

Model Context Protocol over stdio, line-delimited JSON-RPC 2.0
(`br_soccer_mcp_server:loop/1` reads `io:get_line/1`, writes responses to stdout).
Methods: `initialize`, `initialized`, `tools/list`, `tools/call`.

## MCP tools (`tools/call`)

| Tool | Arguments | Returns | Handler |
|------|-----------|---------|---------|
| search_matches | team, season, competition, limit | text list of matches | `br_soccer_mcp_handler:call_tool/3` |
| team_stats | team*, season, competition | W/D/L, goals, points, win rate | `call_tool/3` → `br_soccer_query:team_stats/2` |
| head_to_head | team1*, team2*, season | H2H record + recent matches | `call_tool/3` → `br_soccer_query:head_to_head/3` |
| search_players | name, nationality, club, position, min_overall, limit | ranked FIFA players | `call_tool/3` → `br_soccer_query:search_players/2` |
| competition_standings | competition*, season* | computed table (pts/W/D/L/GD) | `call_tool/3` → `br_soccer_query:compute_standings/1` |
| biggest_matches | competition, season, limit | matches by goal difference | `call_tool/3` → `br_soccer_query:biggest_matches/2` |

(* = required in inputSchema)

## Library API

`br_soccer_query` exports the pure query functions over match/player map lists
(see modules.md). `br_soccer_data:load_all/1` returns
`#{brasileirao, copa_brasil, libertadores, br_football, historical, players}`.

## Data sources

Reads six CSVs from `data/kaggle/`: Brasileirao_Matches, Brazilian_Cup_Matches,
Libertadores_Matches, BR-Football-Dataset, novo_campeonato_brasileiro (matches)
and fifa_data (players). Parsed into lists of `binary => binary` maps keyed by
CSV header; competition tag added on unification.
