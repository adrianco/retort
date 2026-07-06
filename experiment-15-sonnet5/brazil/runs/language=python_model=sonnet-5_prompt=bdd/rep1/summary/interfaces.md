# Interfaces

## MCP tools (FastMCP, stdio transport)

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| search_matches | team, opponent, competition, season, date_from, date_to, limit | formatted match list | `server.py:search_matches` |
| get_head_to_head | team_a, team_b, competition | H2H W/L/D + history | `server.py:get_head_to_head` |
| get_team_record | team, season, competition, venue | W/D/L, goals, win rate | `server.py:get_team_record` |
| compare_teams | team_a, team_b, season, competition | two records + H2H | `server.py:compare_teams` |
| get_top_scoring_teams | competition, season, limit | teams by goals | `server.py:get_top_scoring_teams` |
| search_players | name, nationality, club, position, min_overall, max_age, limit | FIFA players | `server.py:search_players` |
| get_top_rated_players_at_club | club, limit | top players at club | `server.py:get_top_rated_players_at_club` |
| get_brazilian_players_by_club | limit | Brazilian players per Brazilian club | `server.py:get_brazilian_players_by_club` |
| get_standings | competition, season | league table | `server.py:get_standings` |
| get_champion | competition, season | league/cup winner | `server.py:get_champion` |
| get_relegated_teams | competition, season, count | bottom N | `server.py:get_relegated_teams` |
| get_biggest_wins | competition, season, limit | biggest margins | `server.py:get_biggest_wins` |
| get_statistics | competition, season | avg goals/match, home win rate | `server.py:get_statistics` |
| get_best_away_record | competition, season, min_matches, limit | best away win rates | `server.py:get_best_away_record` |

## Library API

`QueryEngine(graph)` exposes the same operations as plain-data methods
(DataFrames/dicts) for direct unit testing; `formatting.py` renders them.

## Data schema

Unified `matches` DataFrame (built from 6 CSVs): match_id, competition,
source, season, round, stage, datetime, date, home_team/home_team_key/
home_team_raw/home_state, away_* counterparts, home_goal, away_goal,
result, stadium, and extended stats (corners, shots, total_corners).

`players` DataFrame (FIFA): player_id, name, age, nationality, overall,
potential, club, club_key, position, plus attributes.

## CLI

`brazilian-soccer-mcp` console script → `server.py:main()` (runs the MCP
server over stdio). Also runnable as `python -m brazilian_soccer_mcp.server`.
