# Interfaces

## MCP tools (`server.py:create_server`)

| Tool | Args | Returns | Backing method |
|------|------|---------|----------------|
| `search_matches` | team, home_team, away_team, team1, team2, season, competition, limit=50 | JSON list of matches | `QueryEngine.search_matches` |
| `get_team_stats` | team, season, competition, home_only=False | JSON dict (W/L/D, goals for/against) | `QueryEngine.get_team_stats` |
| `search_players` | name, nationality, club, position, sort_by="Overall", limit=20 | JSON list of players | `QueryEngine.search_players` |
| `get_head_to_head` | team1, team2 | JSON dict (h2h record + up to 20 matches) | `QueryEngine.get_head_to_head` |
| `get_standings` | season, competition="brasileirao" | JSON list (points-sorted table) | `QueryEngine.get_standings` |
| `get_biggest_wins` | competition, limit=10 | JSON list sorted by goal margin | `QueryEngine.get_biggest_wins` |
| `get_statistics` | competition | JSON dict (avg goals, home win rate, top scoring teams) | `get_average_goals` + `get_home_win_rate` + `get_top_scoring_teams` |

Transport: `FastMCP("brazilian-soccer")`, run via stdio (`server.run()` in `__main__`). All tools return JSON strings (`ensure_ascii=False` for UTF-8 team names).

## Data schema (loaded DataFrames)

Five match datasets unified to a common shape via `_row_to_match`: `home_team`, `away_team`, `home_goal`, `away_goal`, `season`, `date`, `competition` (+ internal `home_team_raw`/`away_team_raw`). Competitions: `brasileirao`, `copa_brasil`, `libertadores`, `br_football`, `historical`. One FIFA player table (`fifa`) with `Name`, `Nationality`, `Club`, `Position`, `Overall`, etc.

## CLI commands

(none) — the module is an MCP stdio server, not a CLI.

## HTTP routes

(none) — MCP protocol over stdio, not HTTP.
