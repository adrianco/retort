# Interfaces

## MCP tools (JSON-RPC `tools/call`)

| Tool | Returns | Handler |
|------|---------|---------|
| search_matches | paginated matches (filters: team, opponent, venue, competition, season, date range, stage, derbies, source) | `soccer.py:SoccerGraph.search_matches` |
| team_stats | W/D/L, goals, by-competition breakdown, FIFA roster | `soccer.py:SoccerGraph.team_stats` |
| head_to_head | per-team W/D/L record + latest meeting | `soccer.py:SoccerGraph.head_to_head` |
| search_players | paginated FIFA players (name/nationality/club/position/min_rating) | `soccer.py:SoccerGraph.search_players` |
| standings | computed league table (Série A/B/C only) | `soccer.py:SoccerGraph.standings` |
| competition_results | cup results + stage counts | `soccer.py:SoccerGraph.competition_results` |
| analysis | avg goals, home win rate, biggest wins, rankings, season trends | `soccer.py:SoccerGraph.analysis` |
| graph_neighbors | edges from team/match/player/competition nodes | `soccer.py:SoccerGraph.graph_neighbors` |
| coverage | provenance, season coverage, warnings, limitations | `soccer.py:SoccerGraph.coverage` |

## JSON-RPC methods

| Method | Behaviour |
|--------|-----------|
| initialize | negotiates protocolVersion, advertises tools capability + instructions |
| ping | `{}` |
| tools/list | 9 tool definitions with inputSchema |
| tools/call | validates args against schema, dispatches to `SoccerGraph` |

Transport: newline-delimited JSON over stdin/stdout. Notifications (no `id`) get no reply;
parse errors return `-32700`, unknown methods `-32601`, bad params `-32602`.

## Data schema (internal)

- **match**: `id, date, home_team, away_team, home_goal, away_goal, competition, season, round, stage, stadium, statistics, sources`
- **player**: `id, name, nationality, club, overall, potential, position, attributes`
- Team names normalized via `team_key()` (accent-folding, alias table, state-suffix disambiguation).
