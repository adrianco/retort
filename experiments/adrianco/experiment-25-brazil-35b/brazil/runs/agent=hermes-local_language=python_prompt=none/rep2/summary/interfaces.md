# Interfaces

## MCP tools (server.py, FastMCP)

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches involving a team (competition/season/date filters) |
| `find_matches_between_teams` | Head-to-head matches + W/L/D summary |
| `find_latest_match` | Most recent match between two teams |
| `find_copa_do_brasil_finals` | Highest-round match per season in cup data |
| `get_team_statistics` | Aggregated W/L/D, goals, home/away split, per-competition breakdown |
| `get_standings` | Season standings computed from match results (3-1-0) |
| `get_champion` | Top of computed standings |
| `get_average_goals` | Avg goals/match + home/draw/away rates |
| `get_biggest_wins` / `get_biggest_wins_by_margin` | Largest goal-margin matches |
| `search_player` | FIFA player name search (partial, case-insensitive) |
| `get_players_by_nationality` | Filter players by nationality + min rating |
| `get_players_by_club` | Filter players by club (+ position, min rating) |
| `get_brazilian_players_at_brazilian_clubs` | Brazilian nationals at Brazilian clubs |
| `get_brazilian_club_summary` | Per-club count/avg/max/min rating |
| `get_team_performance_trend` | Grouped by season or round |
| `get_best_away_record` | Teams ranked by away wins |
| `get_competitions_for_team` | Competitions + seasons a team appears in |
| `get_all_competitions_list` | Distinct competitions |
| `get_dataset_summary` | Match/player counts, date range, per-competition seasons |
| `get_teams_list` | Distinct team names |

## Library API

`QueryEngine(match_data=None, player_data=None)` — instantiable directly; falls back to cached loaders. Tests exercise the engine directly rather than via MCP transport.

## Data schema (unified match DataFrame)

`date` (datetime), `season` (int), `round` (int|None), `competition` (str), `home_team`, `home_goal` (int|None), `away_team`, `away_goal` (int|None).

Player frame (FIFA subset): `Name`, `Age`, `Nationality`, `Overall`, `Potential`, `Club`, `Position`, `Jersey Number`, `Height`, `Weight`.

## HTTP routes / CLI commands

(none) — transport is MCP stdio via `mcp.run()`; console entry point `brazilian-soccer-mcp = server:main`.
