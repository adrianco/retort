# Interfaces

## MCP tools (the public surface)

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| `find_matches` | team, opponent, competition, season, start_date, end_date, limit | `{count, returned, matches[], head_to_head}` | `server.py:find_matches` → `SoccerService.find_matches` |
| `get_team_record` | team, season, competition, venue | `{matches, wins, draws, losses, goals_for, goals_against, points, win_rate, ...}` | `server.py:get_team_record` |
| `compare_teams` | team_a, team_b, season, competition | `{total_matches, team_a_wins, team_b_wins, draws, team_a_goals, team_b_goals, matches[]}` | `server.py:compare_teams` |
| `search_players` | name, nationality, club, position, limit | `{count, returned, players[]}` | `server.py:search_players` |
| `get_standings` | season, competition, limit | `{season, competition, champion, table[]}` | `server.py:get_standings` |
| `get_competition_summary` | competition, season | `{matches, total_goals, avg_goals_per_match, home_wins, away_wins, draws, home_win_rate, biggest_wins[]}` | `server.py:get_competition_summary` |
| `list_team_competitions` | team | `{team, competitions[]}` | `server.py:list_team_competitions` |
| `get_team_profile` | team | `{team, record, competitions[], squad{}}` (cross-file join) | `server.py:get_team_profile` |

Transport: stdio (FastMCP `mcp.run()`).

## Data schema (in-memory pandas tables)

- **matches**: competition, season, date, round, home_team, away_team, home_key, away_key, home_goal, away_goal, source — concatenated from 5 match CSVs, de-duplicated per (competition, season) by source preference.
- **players**: name, age, nationality, overall, potential, club, position, jersey_number, height, weight, club_key — from `fifa_data.csv`.

## CLI

`python demo.py` — prints sample answers (Fla-Flu, 2019 standings, Corinthians record, top Brazilians, Brasileirão stats).
