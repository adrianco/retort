# Interfaces

## MCP transport

JSON-RPC 2.0 over stdio (newline-delimited). Protocol version `2024-11-05`.
Methods handled: `initialize`, `notifications/initialized`, `tools/list`,
`tools/call`, `ping`.

## MCP tools (`tools/call`)

| Tool | Purpose | Key args | Handler |
|------|---------|----------|---------|
| search_matches | Find matches by team/opponent/competition/season(range) | team, home_team, away_team, opponent, competition, season, season_from, season_to, limit | `tools.go:handleSearchMatches` |
| head_to_head | H2H record between two teams | team_a*, team_b*, competition, limit | `tools.go:handleHeadToHead` |
| team_record | Aggregate W/D/L + goals for a team | team*, competition, season, home_only, away_only | `tools.go:handleTeamRecord` |
| search_players | FIFA player search/sort | name, nationality, club, position, min_overall, limit | `tools.go:handleSearchPlayers` |
| players_by_club | Group players by club w/ avg rating | nationality, limit | `tools.go:handlePlayersByClub` |
| competition_standings | League table computed from matches | competition*, season*, limit | `tools.go:handleStandings` |
| match_statistics | Aggregate stats (avg goals, home/away split, biggest wins) | competition, season, team, top_wins | `tools.go:handleStatistics` |
| list_competitions | List competitions + coverage counts | (none) | `tools.go:handleListCompetitions` |

(* = required arg)

## Library API (internal/soccer)

`Load(dir) (*DB, error)`; query methods on `*DB`: `SearchMatches(MatchQuery)`,
`TeamRecord(team, TeamRecordOptions)`, `HeadToHead(a,b,comp)`,
`Standings(comp, season)`, `Statistics(StatsFilter, topWins)`,
`SearchPlayers(PlayerQuery)`, `PlayersByClub(nat, limit)`, `Competitions()`.

## Data schema (in-memory)

- `Match`: competition, season, home/away team (+key/state), goals, date, round/stage, extended stats (shots/corners/attacks), source.
- `Player`: id, name, nationality, club (+key), position, overall, potential, age, physical/value/wage.

## CLI

`brazilian-soccer-mcp [-data DIR]` — `-data` flag or `BR_SOCCER_DATA` env selects the CSV directory (default `data/kaggle`).
