# Interfaces

## MCP tools (server.py via FastMCP)

| Tool | Purpose | Handler |
|------|---------|---------|
| find_matches | Matches by team/opponent/competition/season/venue/date range | `server.py:tool_find_matches` |
| head_to_head | H2H record + match list between two teams | `server.py:tool_head_to_head` |
| team_record | W/D/L, goals, win rate for a team | `server.py:tool_team_record` |
| compare_teams | H2H plus each team's overall record | `server.py:tool_compare_teams` |
| standings | League table computed from match results | `server.py:tool_standings` |
| season_champion | Table-topper for a competition+season | `server.py:tool_season_champion` |
| search_players | FIFA players by name/nationality/club/position/min rating | `server.py:tool_search_players` |
| top_players | Highest-rated players, optionally scoped | `server.py:tool_top_players` |
| biggest_wins | Largest victory margins in dataset | `server.py:tool_biggest_wins` |
| average_goals | Avg goals/match + home/away/draw rates | `server.py:tool_average_goals` |
| best_record | Rank teams by win rate for a venue | `server.py:tool_best_record` |
| list_seasons | Seasons available, optionally per competition | `server.py:tool_list_seasons` |
| list_competitions | Competitions present in dataset | `server.py:tool_list_competitions` |

## Library API (query engine)

`KnowledgeGraph`: `find_matches`, `match_between`, `team_stats`, `head_to_head`,
`compare_teams`, `search_players`, `top_players`, `brazilian_players_by_club`,
`standings`, `champion`, `list_seasons`, `list_competitions`, `biggest_wins`,
`average_goals`, `best_record`. Constructed via `KnowledgeGraph.load(data_dir)`.

## Data schema (normalized records)

- `Match`: competition, season, home_team, away_team, home_goal, away_goal, date,
  round, stage, arena, source, home_key, away_key, stats. Props: winner, is_draw,
  total_goals; `involves(team_key)`, `score_line()`.
- `Player`: player_id, name, age, nationality, overall, potential, club, position,
  jersey_number, height, weight, club_key.

## Data sources (data/kaggle/)

Brasileirao_Matches.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv,
BR-Football-Dataset.csv, novo_campeonato_brasileiro.csv (5 match files) +
fifa_data.csv (players). All six present and loaded.

## HTTP routes / CLI commands

(none — transport is MCP stdio; `demo.py` is a standalone illustration script.)
