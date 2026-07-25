# Interfaces

## Protocol

Plain HTTP/REST via Go's `net/http`. **No MCP server, no JSON-RPC, no tool/resource registration** — the task asked for an MCP server; this exposes a REST API instead.

## HTTP routes

| Method | Path | Query params | Returns | Handler |
|--------|------|--------------|---------|---------|
| GET | /health | — | `{status,matches,players,tournaments}` | `main.go:1248 healthHandler` |
| GET | /api/matches | team1,team2,season,tournament | `[Match]` | `main.go:1096 matchesHandler` |
| GET | /api/team-stats | team,season | `TeamStats` | `main.go:1139 teamStatsHandler` |
| GET | /api/head-to-head | team1,team2 | `{team1_wins,team2_wins,draws}` | `main.go:1157 headToHeadHandler` |
| GET | /api/players | name,club,position,brazilian | `[Player]` | `main.go:1177 playersHandler` |
| GET | /api/standings | season | `[TeamStats]` | `main.go:1209 standingsHandler` |
| GET | /api/biggest-wins | limit | `[Match]` | `main.go:1222 biggestWinsHandler` |
| GET | /api/team-record | team,competition | `TeamStats` | `main.go:1234 teamRecordHandler` |

## Query library (methods on `*SoccerServer`)

`GetMatchesByTeam`, `GetMatchesByTeams`, `GetMatchesByDateRange`, `GetMatchesByTournament`, `GetMatchesBySeason`, `GetTeamStats`, `GetHeadToHead`, `GetPlayerByName`, `GetPlayersByClub`, `GetPlayersByPosition`, `GetBrazilianPlayers`, `GetTopScorersBySeason`, `GetBiggestWins`, `GetTeamRecordByCompetition`, `GetSeasonStandings`.

## Data schema (in-memory structs)

- `Match`: tournament, date, home/away team, home/away goal, season, round, stage, plus extended corner/attack/shot stats.
- `Player`: id, name, age, nationality, overall, potential, club, position, + ~40 FIFA skill ratings.
- `TeamStats`: matches, W/D/L, goals for/against, goal diff, points, with home/away splits.

## Data sources

Loads 6 CSVs from `data/kaggle/` at startup (`LoadData`). Match CSVs load; **`fifa_data.csv` never loads** — see flow.md and findings.
