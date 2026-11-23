# Interfaces

## MCP tools (JSON-RPC over stdio)

| Tool | Purpose | Handler |
|------|---------|---------|
| `find_matches` | Fixtures and scores, newest first; filters by team/opponent/venue/competition/season/date range/stage/source/derby; `biggest_wins` sort; paginated | `soccer.py:Graph.find_matches` |
| `find_players` | FIFA player snapshot ranked by overall; filters by name/nationality/club/position; `details` toggle; paginated | `soccer.py:Graph.find_players` |
| `statistics` | Calculated standings, team W/L/D records, goals_per_match, home_win_rate, competitions; `rank_by` points/wins/win_rate/goals_for | `soccer.py:Graph.statistics` |

## JSON-RPC methods (`server.py:dispatch`)

| Method | Returns |
|--------|---------|
| `initialize` | protocolVersion, capabilities.tools, serverInfo, instructions |
| `tools/list` | `{tools: [...]}` (3 tools with inputSchema) |
| `tools/call` | `{content:[{type:text,text:json}]}` or `{isError:true,...}` |
| `ping` | `{}` |
| (unknown) | JSON-RPC errors −32600/−32601/−32602/−32700 |

## Data schema (in-memory)

Match record: `date, home, away, competition, season, round, stage, home_goal, away_goal, sources[]` (+ `arena` from historical, `statistics` dict from extended dataset).
Player record: raw FIFA columns; default projection `ID, Name, Age, Club, Position, Nationality, Overall, Potential`.

## Source datasets (`data/kaggle/`)

`Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `novo_campeonato_brasileiro.csv`, `BR-Football-Dataset.csv`, `fifa_data.csv` — all six loaded.
