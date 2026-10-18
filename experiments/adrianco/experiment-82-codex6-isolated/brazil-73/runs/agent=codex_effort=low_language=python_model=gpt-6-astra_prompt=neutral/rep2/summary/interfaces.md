# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Behaviour | Handler |
|--------|-----------|---------|
| `initialize` | Validates protocolVersion/capabilities/clientInfo; returns serverInfo + instructions | `server.py:MCPServer.handle` |
| `notifications/initialized` | Marks server ready | `server.py:handle` |
| `ping` | Returns `{}` | `server.py:handle` |
| `tools/list` | Lists the 10 tool schemas | `server.py:handle` |
| `tools/call` | Validates args, dispatches to `SoccerGraph` method, returns text + structuredContent | `server.py:handle` |

## Tools (registered from `SoccerGraph` via reflection)

| Tool | Returns | Backing method |
|------|---------|----------------|
| `search_matches` | Paginated matches (team/opponent/venue/competition/season/date/stage/derbies/source filters) | `soccer.py:258` |
| `team_statistics` | W/D/L, goals, win %, by-competition, snapshot players | `soccer.py:287` |
| `head_to_head` | Symmetric records for two teams + latest match | `soccer.py:296` |
| `search_players` | FIFA players by name/nationality/club/position/min_rating, rating-sorted | `soccer.py:304` |
| `standings` | League table (3/1/0 pts) computed from matches | `soccer.py:324` |
| `bracket` | Cup fixtures grouped by stage/round | `soccer.py:343` |
| `analysis` | Avg goals, home/away/draw rates, biggest wins, team records | `soccer.py:354` |
| `season_comparison` | Aggregate stats or team performance across seasons | `soccer.py:377` |
| `graph_neighbors` | Graph edges for team/player/competition | `soccer.py:384` |
| `dataset_info` | Coverage, source row counts, warnings, limitations | `soccer.py:405` |

## Data schema (in-memory)

- **match**: `id`, `date`, `datetime`, `home_team`, `away_team`, `home_goal`, `away_goal`, `competition`, `season`, `round`, `stage`, `stadium`, `statistics`, `sources[]`
- **player**: `id`, `name`, `age`, `nationality`, `overall`, `potential`, `club`, `position`, `attributes`
- Pagination envelope: `{total, offset, items, next_offset}`

## CLI

`python server.py [--data-dir data/kaggle]` — starts the stdio MCP server.
