# Interfaces

## MCP tools

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| find_matches | team, opponent, competition, season, start_date, end_date, home_away | `{count, matches[], head_to_head}` | `server.py:find_matches` → `KnowledgeBase.find_matches` |
| get_team_record | team (req), season, competition, home_away | `{matches, wins, draws, losses, goals_for, goals_against, win_rate, …}` | `server.py:get_team_record` → `KnowledgeBase.team_record` |
| head_to_head | team1 (req), team2 (req), competition, season | `{total_matches, team1_wins, team2_wins, draws, matches[]}` | `server.py:head_to_head` → `KnowledgeBase.head_to_head` |
| search_players | name, nationality, club, position, min_overall, limit | `{count, players[]}` (sorted by overall desc) | `server.py:search_players` → `KnowledgeBase.search_players` |
| get_standings | season (req), competition=Brasileirão | `{season, competition, standings[], champion}` | `server.py:get_standings` → `KnowledgeBase.standings` |
| get_competition_stats | competition, season | `{matches, average_goals_per_match, home_win_rate, away_win_rate, draw_rate, biggest_wins[]}` | `server.py:get_competition_stats` → `KnowledgeBase.competition_stats` |

Transport: stdio (`FastMCP.run()`); data dir from `BRZ_SOCCER_DATA_DIR` (default `data/kaggle`).

## Data schema (in-memory domain records)

- `Match`: competition, season, date (ISO), home_team, away_team, home_goal, away_goal, round, stage, source.
- `Player`: name, age, nationality, overall, potential, club, position.

## CLI commands

`brazilian-soccer-mcp` console script → `server.main()` (runs the MCP server over stdio). No other subcommands.

## HTTP routes

(none)
