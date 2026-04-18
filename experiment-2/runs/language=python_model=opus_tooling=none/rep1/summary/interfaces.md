# Interfaces

## MCP Tools

The server exposes 7 tools via the Model Context Protocol (FastMCP framework):

| Tool | Signature | Returns | Handler |
|------|-----------|---------|---------|
| `find_matches` | `team`, `opponent`, `season`, `competition`, `limit=50` | JSON array of match records | `server.py:32-45` |
| `head_to_head` | `team_a`, `team_b` | JSON object with W/D/L counts | `server.py:48-51` |
| `team_stats` | `team`, `season`, `competition`, `home_only`, `away_only` | JSON object with wins/draws/losses/goals/points | `server.py:54-65` |
| `standings` | `season`, `competition="Brasileirão"` | JSON array of standings table | `server.py:68-72` |
| `biggest_wins` | `limit=10`, `competition` | JSON array of matches ordered by goal margin | `server.py:75-82` |
| `average_goals` | `competition`, `season` | JSON object with avg goals and home win rate | `server.py:85-88` |
| `search_players` | `name`, `nationality`, `club`, `position`, `min_overall`, `limit=25` | JSON array of player records | `server.py:91-102` |

## Data API

Public classes and functions in `brazilian_soccer/data.py`:

| Symbol | Type | Purpose |
|--------|------|---------|
| `SoccerData` | class | Main dataclass; loads all 6 CSV files, executes queries |
| `normalize_team(name)` | function | Normalizes team names (strips state suffixes, accents, aliases) |
| `get_data()` | function | Cached singleton accessor for SoccerData instance |

## Data Schema

Input CSV files (6 total):
- `Brasileirao_Matches.csv`: home_team, away_team, home_goal, away_goal, season, round, datetime, tournament
- `Brazilian_Cup_Matches.csv`: home_team, away_team, home_goal, away_goal, season, round, datetime, tournament
- `Libertadores_Matches.csv`: home_team, away_team, home_goal, away_goal, season, stage, datetime, tournament
- `BR-Football-Dataset.csv`: home, away, home_goal, away_goal, tournament, corners, attacks, shots, dates
- `novo_campeonato_brasileiro.csv`: Equipe_mandante, Equipe_visitante, Gols_mandante, Gols_visitante, Ano, season, datetime
- `fifa_data.csv`: Name, Age, Nationality, Overall, Club, Position, Jersey Number, and 25+ skill attributes

Unified query interface:
- Match results: datetime, team, goals, tournament, season
- Player data: name, nationality, club, position, rating, attributes
