# Interfaces

## MCP tools (bsoccer/server.py, FastMCP over stdio)

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| find_matches | team, opponent, competition, season, date_from, date_to, side, limit | `{text, data}` match list | `queries.find_matches` |
| team_record | team, competition, season, venue | `{text, data}` W/D/L + goals | `queries.team_record` |
| head_to_head | team_a, team_b, competition, limit | `{text, data}` H2H record | `queries.head_to_head` |
| search_players | name, nationality, club, position, min_overall, sort_by, limit | `{text, data}` player list | `queries.search_players` |
| players_by_club | nationality, top | `{text, data}` per-club summary | `queries.players_by_club_summary` |
| standings | competition, season, top | `{text, data}` league table | `queries.standings` |
| champion | competition, season | `{text, data}` season champion | `queries.champion` |
| list_seasons | competition | `{text, data}` competitions + seasons | `queries.seasons_available` |
| competition_stats | competition, season | `{text, data}` aggregate goal stats | `queries.competition_stats` |
| biggest_wins | competition, season, limit | `{text, data}` largest margins | `queries.biggest_wins` |
| top_scoring_teams | competition, season, limit | `{text, data}` goal ranking | `queries.top_scoring_teams` |

Each tool returns a dual `{"text": <prose>, "data": <structured>}` shape.

## CLI commands (bsoccer/cli.py, `python -m bsoccer.cli`)

`matches`, `record`, `h2h <team_a> <team_b>`, `players`, `standings`, `champion`, `seasons`, `stats`, `biggest` — each mirroring the corresponding query with argparse flags.

## Data schema

- **matches** DataFrame: competition, source, season (int), date (Timestamp), round, home_team, away_team, home_key, away_key, home_goal (Int64), away_goal (Int64), stadium. Unified across 5 match CSVs; `matches_dedup` collapses cross-file Brasileirão overlap.
- **players** DataFrame: FIFA columns (Name, Age, Nationality, Overall, Potential, Club, Position, ...) plus a normalized `club_key`.

## Data sources consumed (data/kaggle/)

`Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`, `fifa_data.csv` — all 6 provided files.
