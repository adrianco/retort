# Interfaces

## MCP tools (JSON-RPC over stdio)

Server speaks line-delimited JSON-RPC 2.0 on stdin/stdout. Methods handled in `mcp.rs:process_message`: `initialize`, `initialized` (notification), `ping`, `tools/list`, `tools/call`, `resources/list`, `prompts/list`.

| Tool | Purpose | Handler |
|------|---------|---------|
| search_matches | Filter matches by team/home_team/away_team/season/competition/date range | `mcp.rs:handle_search_matches` → `query::search_matches` |
| head_to_head | W/L/D + match list between two teams | `mcp.rs:handle_head_to_head` → `query::head_to_head` |
| team_stats | Aggregated W/L/D, goals for/against, points, win-rate | `mcp.rs:handle_team_stats` → `query::team_stats` |
| competition_standings | Computed standings table for a season/competition | `mcp.rs:handle_standings` → `query::standings` |
| search_players | Filter FIFA players by name/nationality/club/min_overall | `mcp.rs:handle_search_players` → `query::search_players` |
| statistics | Aggregate stats: goals_per_match, home_win_rate, biggest_wins | `mcp.rs:handle_statistics` |

## Library API

`Database::load_from_dir(&Path) -> Result<Database>` plus the `query::*` free functions above operate on `&[Match]` / `&[Player]`.

## Data schema (in-memory)

- `Match`: competition (enum), datetime, home_team, away_team, home_goal, away_goal, season, round?, stage?, arena?
- `Player`: id, name, age, nationality, overall, potential, club, position, jersey_number?, height, weight
- `TeamStats`: team, matches, wins, draws, losses, goals_for, goals_against (+ derived points/goal_difference/win_rate)

Source data: 6 CSVs under `data/kaggle/` (Brasileirao, Copa do Brasil, Libertadores, BR-Football extended, historical Brasileirão, FIFA players).
