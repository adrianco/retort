# Interfaces

## HTTP routes

(none) — this is an MCP stdio server, not an HTTP service.

## MCP tools

Registered on a `FastMCP` server (`from mcp.server import FastMCP`), with a fallback to `mcp.Server` and finally an in-process `MockServer` if the SDK is unavailable. Tools are registered via `mcp.tool()(fn)` both at import time and again in `__main__` before `mcp.run()`.

| Tool | Parameters | Returns |
|------|-----------|---------|
| `find_matches_between_teams` | home_team, away_team, competition?, season? | matches between two teams (either orientation) + count |
| `find_matches_by_team` | team, competition?, season?, date_from?, date_to? | matches for one team with opponent/home flag + count |
| `get_team_statistics` | team, season?, competition? | matches_played, wins/losses/draws, win_rate, goals_for/against, goal_difference |
| `find_players_by_club` | club, nationality? | players at a club with overall/position + count |
| `find_players_by_name` | name | players whose name contains the substring + count |
| `find_top_players` | nationality?, club?, min_overall? | top 10 players sorted by overall rating |
| `calculate_statistics` | competition?, season? | total_matches, total_goals, avg goals/match, per-competition breakdowns |
| `find_biggest_victories` | competition?, min_goals=3 | top 10 wins by margin |
| `get_competition_standings` | competition, season | placeholder message only — standings NOT computed |
| `get_head_to_head` | team1, team2, competition?, season? | H2H wins/draws between two teams + raw matches |

## Library API

Each tool is a plain module-level function returning a `Dict[str, Any]`; importable directly (as the tests do). `BrazilianSoccerData` loads/normalizes data on construction; the singleton `soccer_data` is created at import.

## Data schema

Internal match record (dict): `type` (competition), `date`, `home_team`, `home_state`, `away_team`, `away_state`, `home_goals`, `away_goals`, `season`, `round`. Goals and season are kept as strings and coerced with `.isdigit()` checks at use sites.

Internal player record (dict): `name`, `nationality`, `club`, `overall`, `position`. Column indices are detected from the FIFA header, with a positional fallback (name=2, nationality=5, overall=7, club=9, position=24).

Team names are normalized by stripping a trailing `-XX` state suffix (`clean_team_name`). The semicolon-delimited `novo_campeonato_brasileiro.csv` is parsed on its own path; the other match files use `csv.reader`.
