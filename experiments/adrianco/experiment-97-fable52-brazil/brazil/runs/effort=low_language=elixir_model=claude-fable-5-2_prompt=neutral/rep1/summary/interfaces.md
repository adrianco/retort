# Interfaces

## HTTP routes

(none) — this is an MCP stdio server, not an HTTP service.

## MCP transport

Newline-delimited JSON-RPC 2.0 over stdio. Methods handled: `initialize`
(negotiates protocolVersion from `2025-06-18`/`2025-03-26`/`2024-11-05`), `ping`,
`tools/list`, `tools/call`. Notifications (no `id`) are silently accepted; batches
are supported.

## MCP tools (`tools/list`)

| Tool | Purpose | Required args |
|------|---------|---------------|
| search_matches | Find matches by team/opponent/competition/season/date/round/stage; reports head-to-head when team+opponent given | — |
| head_to_head | Two-team W/D/L, goals, recent meetings, home splits | team_a, team_b |
| team_stats | W/D/L record, goals, win rate; home/away and by-competition splits | team |
| team_profile | Cross-dataset profile: competitions, record, recent results, FIFA squad | team |
| standings | League table for a Série A/B/C season computed from matches; champion + relegation | season |
| knockout_bracket | Copa do Brasil / Libertadores season grouped by round/stage; champion on aggregate | competition, season |
| team_rankings | Rank teams by metric (win_rate, points, goals_for, …) over filtered matches | — |
| biggest_wins | Largest winning margins, filterable | — |
| competition_stats | Aggregate stats (avg goals/match, home/draw/away rates); multi-season compare | — |
| derbies | Matches between traditional rivals | — |
| search_players | FIFA player search by name/nationality/club/position/rating/age | — |
| player_details | Full FIFA profile for a player | name |
| brazilian_clubs_players | Per-club summary of FIFA players at Brazilian clubs | — |
| list_teams | List known canonical team names + match counts | — |
| dataset_info | Describe loaded files, row counts, competitions, season coverage | — |

## CLI commands

| Command | Purpose |
|---------|---------|
| `brazilian_soccer_mcp [data_dir]` (escript) | Serve MCP on stdio |
| `mix soccer.mcp [data_dir]` | Same, via Mix task |

Data dir override: `BRAZILIAN_SOCCER_DATA_DIR` env var or first CLI arg.

## Data schema

In-memory `Data` struct: `matches` (`%Match{}` list), `players` (`%Player{}` list),
`teams` (canonical key → %{name, state, matches}), `files` (per-file metadata).
`%Match{}`: id, date, time, season, competition, round, stage, home/away (canonical
keys) + home_name/away_name, home_goals/away_goals, arena, stats, sources.
`%Player{}`: id, name, age, nationality, overall, potential, club, club_key,
position, jersey, height, weight, foot, value, wage, attributes.
Source CSVs: Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches,
BR-Football-Dataset, novo_campeonato_brasileiro, fifa_data.
