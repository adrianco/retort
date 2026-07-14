# Interfaces

## MCP tools (JSON-RPC `tools/call`)

| Tool | Purpose | Required args | Handler |
|------|---------|---------------|---------|
| `search_matches` | Find fixtures by team/opponent/home/away/competition/season/date range | (≥1 filter) | `tools.go:handleSearchMatches` |
| `head_to_head` | W/D/L + goals between two teams | `team_a`, `team_b` | `tools.go:handleHeadToHead` |
| `team_stats` | A team's W/D/L, goals, points, win rate (by season/competition/venue) | `team` | `tools.go:handleTeamStats` |
| `search_players` | FIFA players by name/nationality/club/position/rating | (≥1 filter) | `tools.go:handleSearchPlayers` |
| `competition_standings` | Computed league table from match results | `competition`, `season` | `tools.go:handleStandings` |
| `league_statistics` | summary / biggest_wins / best_home / best_away / best_overall / top_scoring | `metric` | `tools.go:handleLeagueStatistics` |
| `list_competitions` | Dataset coverage (competitions + season ranges) | (none) | `tools.go:handleListCompetitions` |

## MCP protocol methods

| Method | Behavior | Handler |
|--------|----------|---------|
| `initialize` | Handshake, returns protocol version `2024-11-05` + capabilities | `internal/mcp/server.go` |
| `notifications/initialized` | Notification, no response | `internal/mcp/server.go` |
| `tools/list` | Lists registered tools with JSON Schemas | `internal/mcp/server.go` |
| `tools/call` | Dispatches to a tool handler | `internal/mcp/server.go` |
| `ping` | Liveness check | `internal/mcp/server.go` |

## CLI flags (main.go)

| Flag | Purpose |
|------|---------|
| `-data <dir>` | Load CSVs from a directory instead of embedded data |
| `-version` | Print version and exit |

## Data schema

In-memory `DB{ Matches []*Match, Players []*Player }` built from 6 CSVs.
- `Match`: date, competition (canonical key), home/away team (canonical + raw), goals, season, round, stage, arena, optional extended stats (corners/shots/attacks).
- `Player`: id, name, age, nationality, overall, potential, club, position, plus selected FIFA skill ratings.
- Matches are de-duplicated across files via a single authoritative source per (competition, season) bucket.
