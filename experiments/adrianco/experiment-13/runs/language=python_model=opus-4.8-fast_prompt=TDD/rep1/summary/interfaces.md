# Interfaces

## HTTP routes

(none) — this is an MCP server over stdio, not an HTTP service.

## MCP tools (registered in `server.py:build_server`)

| Tool | Args | Returns | Backing logic |
|------|------|---------|---------------|
| `search_matches` | team, team2, competition, season, limit | formatted match list | `SoccerService.search_matches` → `KnowledgeGraph.find_matches` |
| `head_to_head` | team_a, team_b, competition | H2H W/L/D + recent matches | `KnowledgeGraph.head_to_head` |
| `team_record` | team, season, competition, venue | W/L/D, goals for/against, win rate | `KnowledgeGraph.team_record` |
| `search_players` | name, nationality, club, position, min_overall, limit | ranked player list | `KnowledgeGraph.find_players` |
| `standings` | competition, season, limit | computed league table | `KnowledgeGraph.standings` |
| `competition_champion` | competition, season | season champion | `KnowledgeGraph.champion` |
| `statistics` | competition, season | avg goals/match, home win rate, biggest wins | `KnowledgeGraph` stat methods |

## Library API (exported classes/functions)

- `data_loader.load_matches(data_dir) -> list[Match]`, `load_players(data_dir) -> list[Player]`
- `queries.KnowledgeGraph(matches, players)` with `find_matches`, `head_to_head`, `team_record`, `find_players`, `standings`, `champion`, `average_goals_per_match`, `biggest_wins`, `home_win_rate`
- `server.SoccerService(kg)` / `SoccerService.from_data_dir(data_dir)`; `build_server(service) -> FastMCP`

## Data schema

`Match`: competition, home_team, away_team, home_goal, away_goal, season, date, round, stage, source (+ derived `home_key`, `away_key`, `played`, `winner_key`).

`Player`: id, name, age, nationality, overall, potential, club, position, jersey_number, height, weight (+ derived `club_key`, `name_key`).

Data source: 6 CSVs in `data/kaggle/` (5 match files + `fifa_data.csv`).
