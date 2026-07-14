# Interfaces

## MCP tools (`server.py`, registered via `@app.tool()`)

| Tool | Parameters | Returns (dict) |
|------|-----------|----------------|
| `search_matches` | `team?`, `date_from?`, `date_to?`, `competition?`, `season?` | matches list + count; adds `team_statistics` if `team` given |
| `get_team_stats` | `team`, `competition?` | wins/draws/losses/goals/win_rate |
| `get_head_to_head` | `team1`, `team2`, `competition?` | total matches, per-team wins, draws, match list |
| `search_players` | `nationality?`, `club?`, `position?`, `min_overall?`, `max_results=20` | players list + count (sorted by overall) |
| `get_season_standings` | `season`, `competition="Brasileirao"` | points table sorted by points |
| `get_average_goals` | (none) | avg goals/match, home/away/draw win rates |
| `get_top_scoring_matches` | `limit=20` | highest total-goal matches |
| `get_graph_stats` | (none) | node/edge counts by type |
| `find_team_connections` | `team` | teams sharing competitions |
| `get_health_check` | (none) | status, dataset counts per source |
| `find_path_between_teams` | `team1`, `team2`, `max_depth=3` | shortest-path edge list |
| `get_common_opponents` | `team1`, `team2` | teams both have faced |

Every tool wraps its body in try/except and returns `{success, message, data, errors?}`.

## Library API

`MatchDataset` (data_loader.py): `load_all(data_dir)`, `get_match_by_criteria(...)`, `get_team_statistics(team, competition?)`, `get_head_to_head(team1, team2, competition?)`, `get_players_by_filter(...)`, `get_top_scorers_per_match()`, `get_average_goals_per_match()`, `get_standings_by_season(season, competition)`.

`KnowledgeGraph(dataset)` (knowledge_graph.py): `get_node_info(id)`, `get_connected_teams(team, depth)`, `find_path_between_teams(t1, t2, max_depth)`, `get_common_opponents(t1, t2)`, `get_graph_statistics()`, `get_team_neighbors(team)`.

## Data schemas

Source CSVs in `data/kaggle/`: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`, `fifa_data.csv`.

Unified match dict: `date, home_team, away_team, home_goals, away_goals, competition, season, round, stage` (+ corners/shots for extended-stats rows).

Player dict: `id, name, age, nationality, overall, potential, club, position, jersey_number, height, weight, preferred_foot` + `crossing, finishing, dribbling, passing, pace`.

Graph nodes: `team`, `match`, `competition`, `season`, `player`, `player_club`. Edges: `home`, `away`, `played_in`, `has_season`, `plays_for`.

Pydantic models (models.py) mirror these as typed request/response schemas but are not wired into the `@app.tool()` signatures (tools use plain params/dicts).
