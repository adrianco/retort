# Interfaces

## MCP tools (JSON-RPC over stdio, `tools/call`)

| Tool | Purpose | Key args | Handler |
|------|---------|----------|---------|
| search_matches | Find matches across all CSVs | team, opponent, competition, season, date_from, date_to, limit | `main.rs:result` → `lib.rs:Database::matches` |
| team_statistics | W/L/D, goals, points, win-rate for a team | team (req), season, competition, venue | `lib.rs:Database::team_record` |
| head_to_head | Two-team record + their meetings | team_a (req), team_b (req), season, competition | `lib.rs:Database::head_to_head` |
| search_players | FIFA players by name/nationality/club/position, sorted by rating | name, nationality, club, position, limit | `lib.rs:Database::players` |
| standings | Season table computed from match results | season (req), competition | `lib.rs:Database::standings` |
| competition_statistics | Aggregate goals/match, home wins, draws | season, competition | `main.rs:result` (inline) |
| ask | Lightweight NL entry point for player/match lookups | question | `main.rs:result` (keyword routing) |

Protocol methods handled: `initialize`, `tools/list`, `tools/call`, `notifications/initialized` (ignored). Unknown methods return JSON-RPC error -32601.

## Library API (`brazilian_soccer_mcp`)

`Database::load_from_dir(dir)`, `Database::matches(...)`, `team_record(...)`, `head_to_head(...)`, `standings(...)`, `players(...)`; `Record::points()`, `Record::win_rate()`; free fns `normalize()`, `format_match()`.

## Data schema

- **Match**: date, home, away, home_goals, away_goals, competition, season, round, stage.
- **Player**: id, name, age, nationality, overall, potential, club, position.
- Loaded from 5 match CSVs (Brasileirão, Copa do Brasil, Libertadores, BR-Football, novo_campeonato) + `fifa_data.csv`.

## HTTP routes / CLI subcommands

(none) — the binary is a stdio JSON-RPC server, configured via `SOCCER_DATA_DIR` env var (default `data/kaggle`).
