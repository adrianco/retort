# Interfaces

## MCP server (JSON-RPC 2.0 over stdio, protocol `2024-11-05`)

| Method | Returns | Handler |
|--------|---------|---------|
| initialize | protocolVersion, capabilities.tools, serverInfo | `MCPServer.handle` |
| ping | `{}` | `MCPServer.handle` |
| tools/list | `ToolCatalog.definitions` | `MCPServer.handle` |
| tools/call | `{content:[{type:text}], isError}` | `ToolHandler.call` |
| (notification, no id) | no response | `MCPServer.handle` |

## MCP tools (9, advertised by tools/list)

| Tool | Purpose | Key args |
|------|---------|----------|
| search_matches | Find matches by team/opponent/competition/season/date range | team, opponent, competition, season, from, to, venue, newest_first, limit |
| team_record | W/D/L, goals, win rate, goal difference | team* , competition, season, venue |
| head_to_head | H2H record + recent meetings between two teams | team1*, team2*, competition |
| standings | League table computed from results (3/1/0) | season*, competition, limit |
| search_players | FIFA players by name/nationality/club/position/min rating | name, nationality, club, position, min_overall, limit |
| biggest_wins | Largest winning margins | competition, season, limit |
| league_stats | Avg goals/match, home/draw/away rates | competition, season |
| rank_teams | Rank by win_rate/wins/goals_for/points | metric, venue, competition, season, min_played, limit |
| ask | Natural-language question routed to one of the above | question* |

(* = required)

## Data schema (in-memory)

`Match`: date, time, competition, stage, season, home/away (TeamKey + display name), homeGoals, awayGoals, source.
`Player`: id, name, age, nationality, overall, potential, club, position, jerseyNumber, height, weight, preferredFoot, value, wage.

## Data sources (data/kaggle/)

Five match CSVs (Brasileirao, novo_campeonato_brasileiro, Brazilian_Cup, Libertadores, BR-Football-Dataset) deduped by (competition, season); FIFA players from `fifa_data.csv`. ~16.7k matches, ~18k players loaded.
