# Interfaces

## MCP tools (registered in `src/server.ts`)

| Tool | Inputs | Purpose |
|------|--------|---------|
| `search_matches` | team, opponent, venue, competition, season, dateFrom, dateTo, stage, limit | Find matches by any combination of criteria, newest first |
| `head_to_head` | teamA, teamB, competition?, limit? | H2H record + recent matches between two teams |
| `team_record` | team, season?, competition?, venue? | W/D/L record and goals for a team |
| `standings` | season, competition?, top? | League table computed from match results |
| `season_champion` | season | Brasileirão champion for a season |
| `relegated_teams` | season | Bottom-4 relegated teams of a Brasileirão season |
| `competition_stats` | competition?, season? | Goals/match, home/away/draw rates |
| `compare_seasons` | seasons[], competition? | Aggregate stats across several seasons |
| `biggest_wins` | competition?, season?, team?, limit? | Largest victory margins |
| `rank_teams` | competition?, season?, venue?, sortBy?, minMatches?, limit? | Rank teams by winRate/goalsFor/goalsAgainst/points |
| `team_competitions` | team | Competitions a team has played in |
| `derbies` | season?, competition?, limit? | Matches between traditional rivals |
| `search_players` | name?, nationality?, club?, position?, minOverall?, maxAge?, sortBy?, limit? | Search FIFA player data |
| `player_details` | name | Full FIFA profile of a player |
| `brazilian_clubs_players` | nationality? | Players at Brazilian clubs grouped by club |
| `team_profile` | team | Cross-dataset: match record + FIFA squad |
| `dataset_info` | (none) | Loaded files and row counts |

## Data schema (in-memory, `src/data.ts`)

- **Match**: date (ISO), season, competition (`Brasileirão | Copa do Brasil | Libertadores | Serie B | Serie C`), home, away, homeKey, awayKey, homeGoals, awayGoals, round?, stage?, arena?, source, stats?.
- **Player**: id, name, nameKey, age, nationality, overall, potential, club, clubKey, position, jersey, height, weight, value, wage, preferredFoot, skills (34 FIFA attributes).
- **Dataset**: `matches` (deduplicated), `allMatches` (every row), `players`, `bySource` (row counts).

## Data sources

All 6 required CSVs under `data/kaggle/`: `Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `fifa_data.csv`.

## HTTP routes / CLI commands

(none) — the only interface is the MCP stdio tool surface above.
