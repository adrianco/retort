# Interfaces

## HTTP routes

(none — this is an MCP server over stdio, not HTTP.)

## MCP tools (registered via FastMCP `@mcp.tool()`)

| Tool | Args | Returns | Capability |
|------|------|---------|------------|
| find_matches | team, opponent, home_team, away_team, competition, season, season_from/to, date_from/to, limit | `{count, returned, matches[]}` | Match query (R3/R4/R5) |
| last_match | team_a, team_b | `{found, match}` | Match query |
| head_to_head | team_a, team_b, competition | `{wins/draws/goals, matches[]}` | Head-to-head (R11) |
| team_record | team, season, competition, venue | `{played,wins,draws,losses,gf,ga,points,win_rate}` | Team record (R6) |
| compare_teams | team_a, team_b, season | `{team_a_record, team_b_record, head_to_head}` | Team query |
| search_players | name, limit | `{count, players[]}` | Player by name (R7) |
| players_by_club | club, position, limit | `{count, avg_overall, players[]}` | Player by club (R8) |
| players_by_nationality | nationality, limit | `{count, players[]}` | Player by nationality (R8) |
| top_players | nationality, club, position, limit | `{count, players[]}` | Player ratings (R8) |
| standings | season, competition | `{champion, standings[]}` | Standings from results (R9) |
| list_competitions | — | `{competitions[]}` | Metadata |
| list_seasons | competition | `{seasons[]}` | Metadata |
| competition_stats | competition, season | `{avg_goals_per_match, home/away/draw rates}` | Aggregate stats (R10) |
| biggest_wins | competition, season, team, limit | `{matches[] with margin}` | Aggregate stats (R10) |
| best_record | venue, competition, season, min_games, metric, limit | `{teams[]}` | Aggregate stats (R10) |
| database_summary | — | `{total_matches, total_players, competitions, season_range}` | Metadata |

## Data schema (in-memory dataclasses)

- `Match`: date, season, competition, stage, home_team, away_team, home_goal, away_goal, source — plus `involves()`, `has_score`, `winner()`, `total_goals`, `describe()`.
- `Player`: player_id, name, age, nationality, overall, potential, club, position, value, preferred_foot, jersey_number.

## Library API

`SoccerQueryEngine(db=None)` — every capability is also a plain method returning JSON-serializable dicts, so tests exercise them without an MCP runtime.

## Data sources (loaded from `data/kaggle/`)

5 match CSVs (Brasileirão, Copa do Brasil, Libertadores, BR-Football extended, novo_campeonato 2003-2019) + `fifa_data.csv` (18k+ players).
