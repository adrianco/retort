# Interfaces

## MCP tools

Exposed via `FastMCP(name="brazilian-soccer")` in `soccer_mcp/server.py`, run over stdio by `main()` / `python -m soccer_mcp.server`.

| Tool | Parameters | Returns | Delegates to |
|------|-----------|---------|--------------|
| `list_teams` | query? | `list[str]` | `repository.list_teams` |
| `list_competitions` | — | `list[str]` | `repository.list_competitions` |
| `list_seasons` | competition? | `list[int]` | `repository.list_seasons` |
| `find_matches` | team?, opponent?, competition?, season?, date_from?, date_to?, venue?, limit=50 | `list[dict]` | `repository.find_matches` |
| `head_to_head` | team_a, team_b, competition?, season? | `dict` | `repository.head_to_head` |
| `team_record` | team, competition?, season?, venue? | `dict` | `repository.team_record` |
| `standings` | competition, season, min_matches=1 | `list[dict]` | `repository.standings` |
| `biggest_wins` | competition?, season?, n=10 | `list[dict]` | `repository.biggest_wins` |
| `average_goals` | competition?, season? | `dict` | `repository.average_goals` |
| `best_record` | competition?, season?, venue?, min_matches=5, n=10, by="win_rate" | `list[dict]` | `repository.best_record` |
| `search_players` | name?, nationality?, club?, position?, min_overall?, limit=50 | `list[dict]` | `repository.search_players` |
| `top_players` | nationality?, club?, position?, n=10 | `list[dict]` | `repository.top_players` |

## Library API

- `SoccerRepository.from_data_dir(data_dir=None)` — build repository by loading CSVs.
- `SoccerRepository(data: SoccerData)` — build from pre-loaded data; indexes matches by team key.
- `data_loader.load_all(data_dir=None) -> SoccerData` — load + dedupe all six datasets.
- `team_names.normalize_team(raw) -> (canonical_key, display_name)`.

## Data schema (unified in-memory models)

`Match`: source, competition, season, match_date, home_team_key, home_team, away_team_key, away_team, home_goal, away_goal, round?, stage?, venue?, home_team_raw, away_team_raw, extra{}. Derived: `result` (home_win/away_win/draw), `goal_difference`.

`Player`: player_id, name, age, nationality, overall, potential, club, position, jersey_number, height, weight, attributes{20 FIFA skill columns}.

`TeamRecord`: team, matches, wins, draws, losses, goals_for, goals_against. Derived: `points` (3W+D), `win_rate`, `goal_difference`.

## Source datasets (data/kaggle/)

`Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv` (matches); `fifa_data.csv` (players). Overlapping Brasileirao/Copa do Brasil sources are deduped per season by a priority order so aggregates are not double-counted.

## HTTP routes / CLI commands

(none — transport is MCP stdio, not HTTP or an argparse CLI.)
