# Interfaces

## MCP tools (registered in `main.go`, handlers in `tools.go`)

| Tool | Parameters | Returns | Handler |
|------|------------|---------|---------|
| `search_matches` | team, home_team, away_team, competition, season, date_from, date_to, limit | Text + JSON list of matches | `tools.go:HandleSearchMatches` |
| `head_to_head` | team1*, team2*, competition, season | JSON W/D/L + goals from team1's view | `tools.go:HandleHeadToHead` |
| `team_stats` | team*, competition, season | JSON `TeamStats` (W/D/L, goals, points) | `tools.go:HandleTeamStats` |
| `standings` | season, competition | JSON sorted `[]Standing` (top 20) | `tools.go:HandleStandings` |
| `search_players` | name, nationality, club, position, min_overall, limit | Text + JSON list of players | `tools.go:HandleSearchPlayers` |
| `get_statistics` | competition, season, stat_type | JSON aggregate (avg_goals / biggest_wins / best_home_record) | `tools.go:HandleGetStatistics` |

(* = required parameter)

## Library API (query layer)

| Function | Signature (abridged) |
|----------|----------------------|
| `SearchMatches` | `(db, team, homeTeam, awayTeam, competition, season, dateFrom, dateTo, limit) []Match` |
| `HeadToHead` | `(db, team1, team2, competition, season) map[string]interface{}` |
| `GetTeamStats` | `(db, team, competition, season) *TeamStats` |
| `GetStandings` | `(db, season, competition) []Standing` |
| `SearchPlayers` | `(players, name, nationality, club, position, minOverall, limit) []Player` |
| `GetStatistics` | `(db, competition, season, statType) map[string]interface{}` |
| `NormalizeTeam` / `TeamMatches` | team-name normalization + substring match |

## Data schema (in-memory, loaded from CSV)

- `Match`: DateTime, HomeTeam, AwayTeam, HomeGoals, AwayGoals, Season, Round, Stage, Competition (+ BR-Football extras: corners/attacks/shots, Tournament).
- `Player`: ID, Name, Age, Nationality, Overall, Potential, Club, Position, JerseyNumber, Height, Weight.
- `Database`: 5 match slices (Brasileirao, Copa, Libertadores, BRFootball, Historico) + Players slice.

## HTTP routes / CLI commands

(none — transport is MCP over stdio)
