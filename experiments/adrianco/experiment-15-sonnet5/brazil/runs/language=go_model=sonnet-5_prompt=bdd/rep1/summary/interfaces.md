# Interfaces

## MCP transport

Newline-delimited JSON-RPC 2.0 over stdin/stdout. Methods handled
(`mcp.go:handle`): `initialize`, `notifications/initialized`,
`notifications/cancelled`, `ping`, `tools/list`, `tools/call`. Protocol
version `2024-11-05`; server identifies as `brazilian-soccer-mcp` v1.0.0.

## MCP tools (`tools/call`)

| Tool | Purpose | Handler |
|------|---------|---------|
| `search_matches` | Matches by team/opponent/competition/season | `tools.go:handleSearchMatches` |
| `head_to_head` | Full head-to-head record between two teams | `tools.go:handleHeadToHead` |
| `team_record` | W/D/L + goals for a team (season/competition/venue) | `tools.go:handleTeamRecord` |
| `standings` | League table computed from match results | `tools.go:handleStandings` |
| `search_players` | FIFA players by name/nationality/club/position | `tools.go:handleSearchPlayers` |
| `top_players` | Highest-rated players, optionally filtered | `tools.go:handleTopPlayers` |
| `team_players` | FIFA roster joined to a club, avg rating | `tools.go:handleTeamPlayers` |
| `biggest_wins` | Largest victories by goal difference | `tools.go:handleBiggestWins` |
| `stats_summary` | Aggregate stats (avg goals, home/away/draw rates) | `tools.go:handleStatsSummary` |
| `best_record` | Rank teams by win rate (home/away/overall) | `tools.go:handleBestRecord` |

## Data schema (in-memory, `models.go`)

- `Match`: Competition, Source, Date, Season, Round, Stage, HomeTeam/AwayTeam
  (+ normalized keys), HomeGoals/AwayGoals, states, Arena.
- `Player`: ID, Name, Age, Nationality, Overall, Potential, Club (+ key),
  Position, JerseyNumber, Height, Weight.

## Data sources (`loader.go:LoadAll`, default `data/kaggle/`)

`Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`,
`Libertadores_Matches.csv`, `BR-Football-Dataset.csv`,
`novo_campeonato_brasileiro.csv`, `fifa_data.csv`. Matches deduped by
(competition, season, teams, score) to avoid triple-counting overlapping
Brasileirão coverage.

## CLI

`brazilian-soccer-mcp [-data-dir path]` — one flag selecting the CSV directory.
