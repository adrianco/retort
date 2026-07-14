# Interfaces

## MCP tools (registered via `@app.tool()` on a `FastMCP` server)

| Tool | Purpose | Handler |
|------|---------|---------|
| `find_matches` | Matches by team(s), competition, season, date range; H2H summary when two teams | `server.py:48` |
| `get_recent_matches` | Most recent N matches for a team | `server.py:134` |
| `get_team_stats` | W/D/L record, goals for/against, home/away split | `server.py:158` |
| `compare_teams` | Head-to-head + both teams' overall stats | `server.py:215` |
| `find_players` | FIFA players by name/nationality/club/position/min_overall | `server.py:236` |
| `get_player_details` | Full attribute card for best-matching player | `server.py:290` |
| `get_club_players` | All players at a club, sorted by rating | `server.py:328` |
| `get_league_standings` | Season standings computed from match results | `server.py:355` |
| `get_competition_history` | Team's appearances per competition | `server.py:422` |
| `get_top_scorers_teams` | Teams ranked by goals scored | `server.py:450` |
| `get_biggest_wins` | Matches by largest goal difference | `server.py:482` |
| `get_competition_summary` | Aggregate stats (avg goals, home/away/draw %) | `server.py:510` |
| `get_home_away_performance` | Home vs away split, or ranking by home win rate | `server.py:554` |
| `list_seasons` | Distinct seasons in dataset | `server.py:605` |
| `list_teams` | Distinct (normalized) team names | `server.py:620` |

Transport: stdio (`app.run(transport="stdio")`, `server.py:644`).

## Data schema (in-memory pandas DataFrames, `data_loader.py`)

- **Matches** (combined): `datetime, home_team, away_team, home_team_norm, away_team_norm, home_goal, away_goal, season, competition`. Sourced from `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, plus pre-2012 rows from `novo_campeonato_brasileiro.csv` (de-duplicated; `BR-Football-Dataset.csv` loaded separately as `store.br_football`).
- **FIFA players** (`store.fifa`): `Name, Age, Nationality, Overall, Potential, Club, Position`, skill columns, etc.

## HTTP routes / CLI commands

(none — MCP stdio server only.)
