# Interfaces

## MCP tools (server.py)

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| find_matches | team?, season?, competition?, date_from?, date_to?, limit=20 | JSON list of matches | `server.py:find_matches` → `QueryEngine.find_matches` |
| head_to_head | team1, team2 | JSON {wins, losses, draws, matches} | `server.py:head_to_head` |
| get_team_stats | team, competition?, season?, home_only=False, away_only=False | JSON {wins, draws, losses, goals_for, goals_against, matches_played} | `server.py:get_team_stats` |
| find_players | name?, nationality?, club?, position?, min_rating?, limit=20 | JSON list of players | `server.py:find_players` |
| get_standings | season, competition="brasileirao" | JSON list sorted by points | `server.py:get_standings` |
| get_biggest_wins | competition?, limit=10 | JSON list sorted by goal diff | `server.py:get_biggest_wins` |
| competition_averages | competition?, season? | JSON {avg_goals_per_match, home_win_rate} | `server.py:competition_averages` |

Transport: stdio (`mcp.run(transport="stdio")`).

## Library API (query_engine.py / data_loader.py)

- `QueryEngine(loader)` — same seven methods as the tools above.
- `DataLoader(data_dir)` — lazy per-CSV loaders: `load_brasileirao()`, `load_cup()`, `load_libertadores()`, `load_historical()`, `load_extended()`, `load_players()`, `load_all_matches()`.
- Helpers: `normalize_team_name()`, `teams_match()`, `parse_date()`.

## Data schema

Combined matches DataFrame (`load_all_matches`): `home_team`, `away_team`, `home_goal`, `away_goal`, `competition` (one of `brasileirao`/`cup`/`libertadores`/`historical`/`extended`), plus `season` and `date` where available.
Players DataFrame (`fifa_data.csv`): `Name`, `Nationality`, `Overall`, `Club`, `Position`, …

## HTTP routes / CLI commands

(none)
