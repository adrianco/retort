# Interfaces

## MCP tools (the public interface)

| Tool | Key arguments | Returns | Handler |
|------|---------------|---------|---------|
| find_matches | team, opponent, competition, season, date_from, date_to, venue, limit=50 | `{count, matches[]}` | `server.py:find_matches` → `repository.find_matches` |
| head_to_head | team_a, team_b, competition | `{team_a, team_b, total_matches, *_wins, draws, *_goals, matches[]}` | `server.py:head_to_head` → `repository.head_to_head` |
| team_record | team, season, competition, venue | `{matches, wins, draws, losses, goals_for/against, points, win_rate}` | `server.py:team_record` → `repository.team_record` |
| competition_standings | competition, season, limit | `{competition, season, standings[]}` | `server.py:competition_standings` → `repository.standings` |
| competition_winner | competition, season | `{winner}` (top of table) | `server.py:competition_winner` → `repository.competition_winner` |
| list_competitions | — | `{competitions[]}` | `server.py:list_competitions` |
| competition_statistics | competition, season | `{total_matches, total_goals, average_goals_per_match, home_win_rate, ...}` | `server.py:competition_statistics` → `repository.statistics` |
| biggest_wins | competition, season, limit=10 | `{count, matches[]}` (with `margin`) | `server.py:biggest_wins` → `repository.biggest_wins` |
| search_players | name, nationality, club, position, min_overall, limit=50 | `{count, players[]}` | `server.py:search_players` → `repository.search_players` |
| top_players | nationality, club, position, limit=10 | `{count, players[]}` (sorted by overall) | `server.py:top_players` → `repository.search_players` |

## CLI commands

`brazilian-soccer-mcp` (from `pyproject.toml` scripts) → `server.py:main` runs the FastMCP server over stdio. No subcommands/flags. Data dir from `SOCCER_DATA_DIR` env (default `data/kaggle`).

## Data schema (domain models)

- **Match** (`models.py`): competition, competition_type (league/cup), home_team, away_team, home_goal, away_goal, season, date, round, stage, source, stats{}. `to_dict()` emits a `score` string.
- **Player** (`models.py`): id, name, nationality, overall, potential, club, position, age, jersey_number, height, weight.

## Input datasets

6 CSVs under `data/kaggle/`: Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, novo_campeonato_brasileiro (historical), BR-Football-Dataset (extended stats), fifa_data (players). Unknown filenames are ignored by the loader.
