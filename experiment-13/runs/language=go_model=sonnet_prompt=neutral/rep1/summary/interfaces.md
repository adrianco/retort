# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Handling |
|--------|----------|
| `initialize` | Returns protocolVersion `2024-11-05`, tools capability, serverInfo `brazilian-soccer-mcp/1.0.0` (`main.go:261`) |
| `notifications/initialized` | Empty result (`main.go:270`) |
| `ping` | Empty result (`main.go:274`) |
| `tools/list` | Returns the 7 registered tools (`main.go:277`) |
| `tools/call` | Dispatches to `callTool` (`main.go:280`) |

## Tools

| Tool | Args | Purpose | Handler |
|------|------|---------|---------|
| `search_matches` | team, team2, competition, season, limit | Match search + head-to-head (when team2 set) | `tools.go:11` |
| `get_team_stats` | team*, competition, season, home_only | W/L/D record, goals for/against, points, win rate | `tools.go:113` |
| `get_standings` | competition, season*, limit | Points table computed from matches | `tools.go:150` |
| `get_biggest_wins` | competition, season, limit | Matches by largest goal difference | `tools.go:192` |
| `search_players` | name, nationality, club, position, limit | FIFA player search with ratings | `tools.go:228` |
| `get_competition_stats` | competition, season | Avg goals/match, home/away/draw rates, top scorers | `tools.go:289` |
| `list_teams` | competition, season | Distinct teams for a filter | `tools.go:348` |

(* = required in inputSchema)

## Data schema (unified, in-memory)

`Match`: DateTime, HomeTeam, AwayTeam, HomeGoals, AwayGoals, Season, Competition, Round, Stage, Arena, extended stats (corners/attacks/shots). (`data.go:18`)

`Player`: ID, Name, Age, Nationality, Overall, Potential, Club, Position, JerseyNum, Height, Weight, Value, Wage, Foot. (`data.go:39`)

Loaded from 6 CSVs in `data/kaggle/` (5 match files unified + tagged by competition, `fifa_data.csv` for players), with exact-duplicate match dedup. (`data.go:384`)

## CLI / HTTP

(none) — the server speaks MCP over stdin/stdout only.
