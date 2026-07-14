# Interfaces

## MCP transport

JSON-RPC 2.0 over stdio. `Serve` (`server.go:50`) auto-detects framing: raw newline-delimited JSON or LSP-style `Content-Length` headers. Methods handled: `initialize`, `initialized` (notification), `ping`, `tools/list`, `tools/call`. Unknown methods return JSON-RPC error `-32601`.

## MCP tools (`tools.go:GetToolDefinitions`)

| Tool | Purpose | Key params | Handler |
|------|---------|-----------|---------|
| `search_matches` | Matches by team(s)/season/competition | team1, team2, season, competition, limit | `tools.go:SearchMatches` |
| `get_team_stats` | W/L/D, goals for/against, win rate | team*, season, competition, home_only, away_only | `tools.go:GetTeamStats` |
| `search_players` | FIFA player search | name, nationality, club, position, min_overall, limit | `tools.go:SearchPlayers` |
| `get_standings` | Season table computed from matches | season*, competition | `tools.go:GetStandings` |
| `get_head_to_head` | H2H record between two teams | team1*, team2*, competition, limit | `tools.go:GetHeadToHead` |
| `get_biggest_wins` | Largest goal-margin matches | competition, team, season, limit | `tools.go:GetBiggestWins` |

(* = required param)

## Data schema (in-memory)

`Match`: Date, HomeTeam, AwayTeam, HomeGoals, AwayGoals, Season, Competition, Round, Stage, Arena, plus extended corner/shots stats (BR-Football-Dataset only).

`Player`: ID, Name, Age, Nationality, Overall, Potential, Club, Position, JerseyNumber, Height, Weight.

Sources loaded by `LoadAll` (`data.go:295`): `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`, `fifa_data.csv` — all expected under `data/kaggle/`.

## CLI

`./brazilian-soccer-mcp [data-dir]` — optional data dir argument (default `data/kaggle`).
