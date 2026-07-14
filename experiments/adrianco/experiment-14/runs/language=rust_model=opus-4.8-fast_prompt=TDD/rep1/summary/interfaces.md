# Interfaces

## MCP transport

JSON-RPC 2.0 over stdio (newline-delimited). Protocol version `2024-11-05`.
Methods: `initialize`, `ping`, `tools/list`, `tools/call`. Notifications (no `id`) get no reply.

## MCP tools (`tools/call`)

| Tool | Required args | Optional args | Backed by |
|------|---------------|---------------|-----------|
| find_matches | team | opponent, season, competition, limit | `Database::find_matches` (+ head-to-head when opponent given) |
| team_record | team | season, competition, venue (home/away/all) | `Database::team_record` |
| head_to_head | team_a, team_b | season, competition | `Database::head_to_head` |
| standings | season | competition (default Brasileirao) | `Database::standings` |
| search_players | (one of name/club/nationality) | name, nationality, club, position, limit | `players_by_*` + refine |
| top_players | — | nationality, club, limit | `Database::top_players` |
| competition_stats | — | competition, season | `average_goals`, `home_win_rate`, `most_goals_team`, `biggest_wins` |
| last_match | team_a, team_b | — | `Database::last_match_between` |

## Library API (query::Database)

`load(dir)`, `find_matches(filter)`, `matches_between(a,b)`, `team_record(team,filter,home_only,away_only)`, `head_to_head(a,b,filter)`, `standings(comp,season)`, `players_by_name/nationality/club`, `top_players`, `average_goals`, `home_win_rate`, `biggest_wins`, `most_goals_team`, `best_venue_record`, `last_match_between`.

## Data sources (data/kaggle/)

5 match CSVs → unified `Match` (Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset, novo_campeonato_brasileiro) + `fifa_data.csv` → `Player`. Overlapping fixtures de-duplicated per (competition, season) by `source_priority`.
