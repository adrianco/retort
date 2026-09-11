# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Behavior | Handler |
|--------|----------|---------|
| `initialize` | Negotiates protocol version, advertises `tools` capability + serverInfo | `main.go:Serve` |
| `ping` | Empty result | `main.go:Serve` |
| `tools/list` | Returns the 7 tool definitions (requires prior initialize) | `main.go:toolList` |
| `tools/call` | Dispatches to `Graph.Query`; unknown-field args rejected | `main.go:Serve` → `query.go:Query` |

Errors use JSON-RPC codes: -32700 parse, -32600 invalid request, -32601 method not found, -32602 invalid params, -32002 not-initialized. Notifications (no `id`) are skipped.

## Tools (each maps to a `Graph.Query` case)

| Tool | Required args | Returns |
|------|---------------|---------|
| `search_matches` | — | `{total, matches[]}` with pagination (limit/offset), team/opponent/venue/date/season/competition/round/stage/source/derbies filters, `biggest_win` sort |
| `search_players` | — | `{total, players[]}` filtered by name/nationality/club/position, sorted by overall |
| `team_info` | `team` | record, home/away splits, by_competition, by_season, competitions, matches, linked players |
| `head_to_head` | `team`, `opponent` | W/L/D + goals from `team`'s perspective |
| `standings` | `competition`, `season` | Brasileirão league table computed from matches (3/1/0 points) |
| `statistics` | — | avg goals/match, home win rate, draws, by_season, team rankings (win-rate or goals) |
| `data_info` | — | source row counts, unique match count, player count, warnings |

## Data schema

`Match`: id, date, home, away, home_goals*, away_goals*, competition, season, round, stage, sources[], records[] (\*nullable score pointers).
`Player`: id, name, club, nationality, position, overall, attributes (raw CSV row).
`Record`: team, played, wins, draws, losses, goals_for, goals_against, goal_difference, points, win_rate.

## CLI

`-data <dir>` (default `data/kaggle`) — directory of the six CSV datasets.
