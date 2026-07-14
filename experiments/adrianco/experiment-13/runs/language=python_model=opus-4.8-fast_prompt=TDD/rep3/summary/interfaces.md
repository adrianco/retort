# Interfaces

## MCP tools (FastMCP, stdio)

Registered in `server.py:build_server`; each delegates to a `service.answer_*` formatter.

| Tool | Parameters | Returns | Handler |
|------|-----------|---------|---------|
| `find_matches` | team, opponent, competition, season, start_date, end_date, venue, limit | formatted match list (+ H2H when team & opponent) | `service.answer_find_matches` |
| `head_to_head` | team1, team2, competition?, season? | H2H record + recent meetings | `service.answer_head_to_head` |
| `team_record` | team, competition?, season?, venue | W/D/L, goals, points, win rate | `service.answer_team_record` |
| `standings` | competition, season | computed league table | `service.answer_standings` |
| `search_players` | name?, nationality?, club?, position?, min_overall?, limit | ranked player list | `service.answer_search_players` |
| `competition_stats` | competition?, season? | aggregate goal/home/away/draw stats | `service.answer_competition_stats` |
| `biggest_wins` | competition?, season?, limit | matches by goal margin | `service.answer_biggest_wins` |
| `list_competitions` | — | competition labels | `service.answer_list_competitions` |
| `list_seasons` | competition? | season list | `service.answer_list_seasons` |

## Library API

`SoccerKB.from_data_dir(data_dir)` loads CSVs; methods mirror the tools above and return structured `dict`/`list[Match]`/`list[Player]`.

## Data schema (in-memory dataclasses)

- `Match`: competition, home_team, away_team, home_score, away_score, season, date, round, stage, source, extended stats (corners/shots), `home_key`/`away_key` (match keys). Properties: `total_goals`, `winner_key`, `signature()`.
- `Player`: id, name, age, nationality, overall, potential, club, position, jersey_number, height, weight, `name_key`.

## Data sources

6 CSVs under `data/kaggle/`: 5 match files (`Brasileirao_Matches`, `novo_campeonato_brasileiro`, `Libertadores_Matches`, `Brazilian_Cup_Matches`, `BR-Football-Dataset`) → unified `Match` set with per-`(competition, season)` source-priority de-duplication; `fifa_data.csv` → `Player` set.
