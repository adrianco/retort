# Interfaces

## MCP transport

Newline-delimited JSON-RPC 2.0 over stdio (hand-rolled, no SDK). Supports MCP
protocol versions 2024-11-05 through 2025-11-25. Methods: `initialize`,
`notifications/initialized`, `ping`, `tools/list`, `tools/call`.

## MCP tools (`tools/call`)

| Tool | Purpose | Required args | Handler |
|------|---------|---------------|---------|
| search_matches | Find fixtures by team/opponent/venue/date/competition/season/stage/source/derby; sortable | — | `query.go:Call` → `matches` |
| search_players | FIFA player search by name/nationality/club/position/min_rating | — | `query.go:Call` → `players` |
| team_profile | Team fixtures + aggregate W/L/D record + competitions + FIFA roster | `team` | `query.go:Call` |
| head_to_head | Two-team W/L/D, goals, recent meetings | `team`, `opponent` | `query.go:Call` |
| standings | League table computed from matches (3pts/win) | `competition`, `season` | `query.go:Call` → `records` |
| statistics | Aggregate goals/match, home vs away, team records; group by season/competition | — | `query.go:Call` → `summary` |
| competition_results | Schedules/results + stage counts for a competition | `competition` | `query.go:Call` |
| data_info | Dataset coverage, source counts, dedup conflicts, limitations | — | `query.go:Call` |

## CLI

`soccer-mcp -data <dir>` (default `data/kaggle`). Loads CSVs, prints match/player
counts to stderr, then serves MCP on stdin/stdout.

## Data schema (loaded, in-memory)

`Match`: id, date, competition, season, round, stage, home, away, home_goals,
away_goals, stadium, sources[], attributes{}.
`Player`: id, name, nationality, club, position, overall, potential, attributes{}.

Sources: Brasileirao_Matches.csv, Brazilian_Cup_Matches.csv,
Libertadores_Matches.csv, BR-Football-Dataset.csv, novo_campeonato_brasileiro.csv,
fifa_data.csv.
