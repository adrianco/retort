# Interfaces

## Protocol

MCP (Model Context Protocol) JSON-RPC 2.0 over stdio, stdlib-only (no SDK dependency
in the server itself). Methods: `initialize`, `ping`, `tools/list`, `tools/call`,
`notifications/*`. Supports protocol versions 2025-06-18, 2025-03-26, 2024-11-05;
emits `structuredContent` on ≥ 2025-06-18.

## MCP tools (`tools/call`)

| Tool | Purpose | Handler |
|------|---------|---------|
| search_matches | Matches by team/opponent/competition/season/date/venue/stage | `queries.search_matches` |
| head_to_head | H2H record, last meeting, biggest win, per-competition split | `queries.head_to_head` |
| team_record | W/D/L, goals, win rate, points, venue split | `queries.team_record` |
| team_profile | Cross-file club overview: competitions, titles, FIFA squad | `queries.team_profile` |
| standings | Season table computed from results; champion/relegated | `queries.standings` |
| knockout_bracket | Knockout ties w/ aggregates (Libertadores / Copa do Brasil) | `queries.knockout_bracket` |
| finals | Finals with aggregate & winner | `queries.finals` |
| team_rankings | Rank teams by metric (win_rate/points/goals/…) | `queries.team_rankings` |
| competition_stats | Goals/match, home/draw/away rates, scorelines, corners/shots | `queries.competition_stats` |
| biggest_wins | Largest victory margins | `queries.biggest_wins` |
| derbies | Matches between recognised rivals | `queries.derbies` |
| compare_seasons | Side-by-side stats for two seasons | `queries.compare_seasons` |
| search_players | FIFA players by name/nationality/club/position/rating/age | `queries.search_players` |
| player_profile | Detailed single-player profile + similar names | `queries.player_profile` |
| club_players | Players at a club + club match record (cross-file) | `queries.club_players` |
| brazilian_players_overview | Top Brazilians + per-club summary | `queries.brazilian_players_overview` |
| find_team | Resolve/normalise a team name | `queries.find_team` |
| dataset_info | Loaded files, row counts, merges, coverage | `queries.dataset_info` |

## Data schema (internal)

- `Match`: home/away `Team`, home_goals/away_goals, season, round, stage, competition, date, `stats` (corners/shots/attacks where available), sources.
- `Player`: name, age, nationality, overall, potential, club, `club_team`, position, physical attributes, value/wage.
- `SoccerDB`: unified `matches`, `matches_by_team` index, `players`, source/skipped/merged row counts.

## CLI / scripts

- `python -m brsoccer` / `mcp_server.py` — run the MCP server on stdio.
- `brazilian-soccer-mcp` — console entry point (`brsoccer.server:main`).
- `demo.py` — scripted demonstration (not part of the server).
