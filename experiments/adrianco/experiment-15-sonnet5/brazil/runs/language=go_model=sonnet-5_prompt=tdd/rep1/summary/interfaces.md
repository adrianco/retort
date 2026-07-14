# Interfaces

## HTTP routes

(none) — the server speaks MCP over stdio (`mcp.StdioTransport`), not HTTP.

## MCP tools

Registered in `internal/mcpserver/server.go` via `mcp.AddTool`. All results are returned as plain-text `TextContent`.

| Tool | Args | Returns | Backing store method |
|------|------|---------|----------------------|
| `find_matches` | team, opponent, competition, season, from, to, limit | Formatted match list | `Store.FindMatches` |
| `head_to_head` | team_a, team_b | Match list + win/draw record | `Store.HeadToHead` |
| `team_record` | team, season, competition, venue (home/away) | W/D/L record, goals, win rate | `Store.TeamRecord` |
| `standings` | competition, season | Points table computed from results | `Store.Standings` |
| `biggest_wins` | competition, season, limit (default 10) | Most lopsided decisive matches | `Store.BiggestWins` |
| `stats_summary` | team, competition, season | Avg goals/match, home/away/draw rates | `Store.StatsSummary` |
| `search_players` | name, nationality, club, position, min_overall, limit (default 25) | Players sorted by overall desc | `Store.SearchPlayers` |

## CLI commands

Single binary `cmd/server`. One flag:

| Flag | Default | Description |
|------|---------|-------------|
| `-data-dir` | `data/kaggle` | Directory containing the six source CSV datasets |

## Library API (internal/soccer)

- `LoadStoreFromDir(dir) (*Store, error)` — loads all six CSVs.
- `Store` query methods: `FindMatches`, `HeadToHead`, `TeamRecord`, `Standings`, `BiggestWins`, `StatsSummary`, `SearchPlayers`.
- Helpers: `NormalizeTeamKey(name)`, `ParseDate(s)`, `Match.Outcome()`.

## Data schema (in-memory models)

`Match`: Date, Season, Round, Stage, Competition, Source, HomeTeam, AwayTeam, HomeKey, AwayKey, HomeGoals, AwayGoals, HomeState, AwayState, Stadium.

`Player`: ID, Name, Age, Nationality, Overall, Potential, Club, Position, JerseyNumber, Height, Weight.

Source CSVs are normalized into these two structs. Competitions are tagged per-loader: `Brasileirao`, `Copa do Brasil`, `Libertadores`, `Brasileirao (Historical)`, and per-row `tournament` for `BR-Football-Dataset.csv`. No persistent database — all data is held in slices in memory.
