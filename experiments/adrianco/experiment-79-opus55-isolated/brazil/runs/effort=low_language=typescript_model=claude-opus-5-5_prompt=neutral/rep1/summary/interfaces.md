# Interfaces

## MCP tools (registered in `src/server.ts` from `src/tools.ts`)

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team/opponent/home/away, competition, season, date range, stage |
| `head_to_head` | W/D/L + goals + meetings between two teams |
| `team_stats` | W/D/L record, goals for/against, win rate for a team (season/comp/venue) |
| `team_overview` | Cross-file team summary: competitions, records, FIFA squad |
| `standings` | League table computed from results (3pts/win), champion/relegation tags |
| `competition_knockout` | Cup bracket by stage with inferred final winner |
| `rank_teams` | Rank teams by winRate/points/wins/goalsFor, overall or home/away |
| `league_stats` | Aggregate stats: matches, goals, avg goals/match, home/draw/away rates |
| `biggest_wins` | Largest winning margins (filterable) |
| `compare_seasons` | Compare two seasons of a competition |
| `find_derbies` | Matches between traditional rivals |
| `search_players` | FIFA search by name/nationality/club/position/rating |
| `player_profile` | Detailed player profile + recent club matches |
| `brazilian_club_squads` | Brazilian clubs in FIFA data: size, avg rating, best player |
| `dataset_info` | Row counts, competitions, seasons, dedup match totals |

## Data schema (from `src/data.ts`)

- `Match`: competition, season, date, round/stage, home/away, goals, arena, stats, sources
- `Player`: id, name, age, nationality, overall/potential, club/clubId, position, attributes, skills
- `Dataset`: matches[], players[], teams (TeamRegistry), rowCounts

## Data source

Six CSVs under `data/kaggle/` (`Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`,
`Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`,
`fifa_data.csv`), loaded and de-duplicated by `loadDataset()`; overridable via
`BRAZILIAN_SOCCER_DATA_DIR`.
