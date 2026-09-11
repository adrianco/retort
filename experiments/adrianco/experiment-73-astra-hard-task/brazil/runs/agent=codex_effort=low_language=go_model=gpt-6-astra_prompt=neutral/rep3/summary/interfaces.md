# Interfaces

## Transport

MCP over stdio, newline-delimited JSON-RPC 2.0 (`main.go:Serve`). Handshake: `initialize` → `notifications/initialized` → tools become callable. Also handles `ping`. Negotiates protocol versions `2024-11-05` / `2025-03-26` / `2025-06-18`.

## MCP tools (`main.go:toolList`) — 9 tools

| Tool | Purpose | Required args | Handler |
|------|---------|---------------|---------|
| search_matches | Search fixtures/results across the 5 match CSVs (team/opponent/venue/date/competition/season/stage/derbies/sort) | — | `query.go:FindMatches` → `matchPage` |
| team_stats | W/L/D, goals for/against, win rate, home/away split, by-competition & by-season | team | `query.go:TeamStats` |
| head_to_head | Two-team records in both directions + paginated match list | team, opponent | `query.go:FindMatches` + `teamRecord` |
| standings | Calculated league table for Brasileirão/Serie B by season | competition, season | `query.go:Standings` |
| statistics | Goals/match, home/away win rates, ranked team records | — | `query.go:Statistics` |
| competition_results | Schedule/results with stage-grouped match IDs (bracket evidence) | competition, season | `query.go:FindMatches` |
| search_players | FIFA search by name/nationality/club/position/min_overall, club aggregates | — | `query.go:FindPlayers` |
| team_graph | Typed team↔match↔competition↔player edges (knowledge graph) | team | `query.go:Graph` |
| dataset_info | Sources, row counts, coverage, warnings, limitations | — | inline in `main.go:Call` |

## Data schema

- **Match**: id, date, home_team, away_team, competition, season, round, stage, home_goal, away_goal, stadium, sources[] (raw provenance).
- **Player**: id, name, nationality, club, position, overall, potential, attributes{} (full FIFA row retained).
- **Record**: team, played, wins, draws, losses, goals_for/against, goal_difference, points, win_rate_percent.

## Data sources (`data.go:datasetFiles`)

Loads all 6 CSVs from `data/kaggle/`: Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, novo_campeonato_brasileiro, BR-Football-Dataset (extended stats), fifa_data.

## CLI

`-data <dir>` flag (default `data/kaggle`).
