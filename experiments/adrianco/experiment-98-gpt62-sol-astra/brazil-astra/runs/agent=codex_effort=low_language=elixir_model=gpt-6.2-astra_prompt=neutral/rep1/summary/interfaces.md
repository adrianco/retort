# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | protocolVersion, capabilities, serverInfo | `server.ex:dispatch/3` |
| `ping` | `{}` | `server.ex:dispatch/3` |
| `tools/list` | `{tools: [...]}` with JSON schemas | `server.ex:dispatch/3` |
| `tools/call` | `{content: [{type: "text", text: <json>}]}` or `{isError: true, ...}` | `server.ex:dispatch/3` |
| notifications (no `id`) | no response (nil) | `server.ex:process/2` |

Error codes: `-32700` parse error, `-32600` invalid request, `-32601` method not found, `-32602` invalid/unknown params/tool.

## MCP tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `team_profile` | Team record + latest 5 fixtures + top 5 FIFA players | `team` (required), `season`, `competition` |
| `matches` | Find fixtures/scores, latest first; head-to-head via team+opponent | `team`, `opponent`, `venue`, `competition`, `source`, `season`, `stage`, `derby`, `from`, `to`, `limit`, `offset` |
| `players` | Search FIFA players by name/club/nationality/position | `name`, `club`, `nationality`, `position`, `limit`, `offset` |
| `statistics` | Goals/match, home-win %, W/D/L; group by season/venue/competition | match filters + `group_by` |
| `standings` | Rank teams by points/goals/win_rate, or individual wins by `margin` | match filters + `rank_by`, `limit`, `offset` |

## Data schema (in-memory)

- **match**: `date`, `season`, `competition` (Serie A / Copa do Brasil / Libertadores), `round`, `stage`, `home`, `away`, `home_goal`, `away_goal`, `source`, `details` (raw row).
- **player**: `club`, `name`, `nationality`, `rating` (FIFA Overall), `data` (raw FIFA row).
- **Sources**: `data/kaggle/{Brasileirao_Matches, novo_campeonato_brasileiro, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset}.csv` + `fifa_data.csv`.

## CLI / Library API

- `Soccer.Server.main/1` — escript entrypoint; optional arg overrides the data directory.
- `Soccer.Query.run/3` — library query surface, directly exercised by tests.
