# Interfaces

## MCP tools (`server.py`)

| Tool | Purpose | Backing query |
|------|---------|---------------|
| `dataset_info` | Files, row counts, competitions & seasons loaded | `queries.py:dataset_info` |
| `find_team` | Search team names, show canonical name + variants | `queries.py:find_team` |
| `search_matches` | Matches by team/opponent/competition/season/date/venue/stage | `queries.py:search_matches` |
| `head_to_head` | Head-to-head W/D/L, goals, home/away split | `queries.py:head_to_head` |
| `team_record` | W/D/L, goals for/against, win rate (optional home/away) | `queries.py:team_record` |
| `team_overview` | Cross-dataset team profile (records, titles, derbies, squad) | `queries.py:team_overview` |
| `team_trend` | Season-by-season league position/points | `queries.py:team_trend` |
| `standings` | League table computed from matches, champion + relegated | `queries.py:standings` |
| `team_rankings` | Rank teams by a metric (points, goals, win_rate, …) | `queries.py:team_rankings` |
| `competition_stats` | Aggregate stats: goals/match, home/draw/away, corners, shots | `queries.py:competition_stats` |
| `compare_seasons` | Side-by-side season comparison | `queries.py:compare_seasons` |
| `biggest_wins` | Largest victory margins | `queries.py:biggest_wins` |
| `knockout_results` | Cup knockout ties / brackets with aggregate scores | `queries.py:knockout_results` |
| `derby_matches` | Matches between traditional rivals | `queries.py:derby_matches` |
| `search_players` | FIFA 19 search by name/nationality/club/position/rating/age | `queries.py:search_players` |
| `player_profile` | Detailed FIFA 19 player profile | `queries.py:player_profile` |
| `player_club_summary` | Top players per nationality + per-club counts/ratings | `queries.py:player_club_summary` |

## MCP resources

| URI | Returns |
|-----|---------|
| `soccer://dataset-info` | Text summary of loaded datasets |

## Transports

- stdio (default): `python server.py`
- streamable HTTP: `python server.py --http <PORT>`

## Data schema (loaded into memory)

- `Match`: competition, season, date, home/away team ids, goals, stage, extended stats (corners/shots/attacks).
- `Player`: FIFA 19 fields — name, age, nationality, overall/potential, club, position, skills.
- Six CSVs under `data/kaggle/`: `Brasileirao_Matches.csv` (4180), `Brazilian_Cup_Matches.csv` (1337), `Libertadores_Matches.csv` (1255), `BR-Football-Dataset.csv` (10296), `novo_campeonato_brasileiro.csv` (6886), `fifa_data.csv` (18207).
