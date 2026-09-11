# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Behavior | Handler |
|--------|----------|---------|
| `initialize` | Negotiates `protocolVersion`, advertises tool capability + serverInfo | `server.py:MCPServer.handle` |
| `notifications/initialized` | Marks server ready (no response) | `server.py:MCPServer.handle` |
| `ping` | Empty result | `server.py:MCPServer.handle` |
| `tools/list` | Returns all 13 tool schemas with annotations | `server.py:MCPServer.handle` |
| `tools/call` | Validates args by type + required, dispatches to graph method | `server.py:MCPServer.handle` |

## Tools (13, all read-only)

| Tool | Returns | Backing method |
|------|---------|----------------|
| `search_matches` | Paginated matches by team/opponent/venue/date/competition/season/stage/source/derbies | `soccer.py:search_matches` |
| `search_players` | Paginated FIFA players by name/nationality/club/position/min_rating | `soccer.py:search_players` |
| `team_statistics` | W/L/D, goals for/against, points, win rate | `soccer.py:team_statistics` |
| `head_to_head` | Two-team record + matches | `soccer.py:head_to_head` |
| `standings` | Computed league table (Brasileirão/Serie B/C only) | `soccer.py:standings` |
| `analysis` | avg goals, home win rate, biggest wins | `soccer.py:analysis` |
| `team_profile` | Stats + competitions + FIFA roster | `soccer.py:team_profile` |
| `trends` | Per-season stats/analysis | `soccer.py:trends` |
| `competition_results` | Fixtures grouped by stage/round | `soccer.py:competition_results` |
| `top_scorers` | Explains why unavailable | `soccer.py:top_scorers` |
| `coverage` | Row counts, date range, errors, conflicts | `soccer.py:coverage` |
| `neighbors` | Graph edges for team/player/competition/match | `soccer.py:neighbors` |

## Data schema (in-memory)

- **match**: `id, date, home_team, away_team, home_goal, away_goal, competition, season, round, stage, stadium, sources[], statistics`
- **player**: `id, name, club, nationality, position, overall, potential, age, attributes`
- Sources: 5 match CSVs (Brasileirão, Copa do Brasil, Libertadores, BR-Football extended, historical 2003–2019) + `fifa_data.csv`; matches deduplicated across files with ±1-day cross-source reconciliation.
