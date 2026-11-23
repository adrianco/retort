# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| initialize | protocolVersion, capabilities, serverInfo, instructions | `main.go:dispatch` |
| ping | `{}` | `main.go:dispatch` |
| tools/list | `{tools: [...]}` | `main.go:dispatch` |
| tools/call | `{content: [{type:text, text}]}` or `{isError:true}` | `main.go:dispatch` |

Protocol version negotiated: `2025-06-18` (accepts `2024-11-05`, `2025-03-26`, `2025-06-18`).

## MCP tools

| Tool | Purpose | Key args |
|------|---------|----------|
| search_matches | Fixtures/scores newest-first across reconciled sources | team, opponent, side, competition, season, season_from/to, date_from/to, round, stage, source, derby, status, offset, limit |
| team_stats | Club W/L/D, goals, win rate, home/away splits, by-competition/season; head-to-head via opponent | team (required), opponent, side, competition, season, ... |
| search_players | FIFA snapshot search ordered by overall | name, nationality, club, position, brazilian_clubs, min_overall, include_attributes, group_by_club, offset, limit |
| competition_standings | Série A/B standings computed from matches; champion/relegation flags, coverage flag | season (required), competition |
| analyze_matches | Aggregate stats: summary (goals/match, home/away win rate), goals_for, win_rate ranking, biggest_wins | metric, competition, season, side, minimum_matches, ... |
| club_profile | Joins a club's match record + competitions to its FIFA roster | team (required), season, competition, ... |

## Data schema (internal)

- `Match`: date, kickoff, home/away (+state), home/away_goals (nullable), competition, season, round, stage, historical_id, stadium, statistics (map), sources[].
- `Player`: id, name, age, nationality, club, overall, potential, position, attributes (map).
- `Store`: reconciled `matches[]`, per-source `bySource`, `players[]`.

## CLI

`-data-dir` flag (default `data/kaggle`) — directory holding the six Kaggle CSVs.
