# Interfaces

## MCP protocol

**(none)** — no MCP SDK, no JSON-RPC / stdio transport, no tool-schema registration.
`go.mod` declares zero dependencies. The "tools" are plain Go methods on `Server`
that are never advertised or dispatched over any protocol.

## HTTP routes

**(none)** — `Server.Run()` logs `"Server listening"` and prints a tool list, but
starts no listener; it returns `nil` immediately. `main()` then blocks on `select {}`.

## Library API (tool-shaped handlers, `main.go`)

Each takes `(ctx, params map[string]interface{})` and returns `(map[string]interface{}, error)`:

| Handler | Backing query fn | Purpose |
|---------|------------------|---------|
| `HandleSearchMatches` | `SearchMatches` | filter matches by home/away team, tournament, season (+ limit/offset) |
| `HandleGetTeamStats` | `GetTeamStats` | W/L/D, goals for/against, points for a team |
| `HandleGetHeadToHead` | `GetTeamHeadToHead` | head-to-head record between two teams |
| `HandleSearchPlayers` | `SearchPlayers` | filter players by name/nationality/club/position/min-overall |
| `HandleGetTopScorers` | `GetTopScorers` | teams ranked by goals for |
| `HandleGetStandings` | `CalculateStandings` | season standings computed from results |
| `HandleGetBiggestWins` | `GetBiggestWins` | matches with largest goal difference |
| `HandleGetRecentMatches` | `GetRecentMatches` | most-recent matches for a team |
| `HandleGetTeamMatches` | `GetTeamMatches` | all matches for a team (opt. tournament) |
| `HandleGetMatchesBetweenTeams` | `GetMatchesBetweenTeams` | matches involving both named teams |

## Data schema

- `Match`: id, tournament, home/away team+state, home/away goal, datetime, season, round, stage, plus BR-Football extras (corners/attacks/shots).
- `Player`: id, name, age, nationality, overall, potential, club, position, jersey, skills.
- `TeamStats` / `TeamHeadToHead` / `CompetitionStandings`: aggregate result structs.

## Data sources

Reads all 6 provided CSVs from `data/kaggle/` (5 match files + `fifa_data.csv`).
