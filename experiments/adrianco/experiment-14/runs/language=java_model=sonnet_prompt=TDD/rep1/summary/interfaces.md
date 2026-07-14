# Interfaces

## MCP tools (stdio transport)

| Tool | Required args | Optional args | Returns |
|------|---------------|---------------|---------|
| `find_matches` | — | team, competition, season, limit | Formatted match list (default limit 20) |
| `get_team_stats` | team | competition, season | Played/W/D/L, goals for/against, points |
| `find_players` | — | name, nationality, club, top, limit | Formatted player list with overall/potential |
| `get_head_to_head` | team1, team2 | — | Total matches, per-team wins, draws |
| `get_standings` | season | competition (default Brasileirao) | Points-sorted standings table |
| `get_biggest_wins` | — | limit, competition | Matches sorted by goal difference |

## Library API (exported)

- `MatchService`: `findByTeam`, `findByTeams`, `findByCompetition`, `findBySeason`, `findBySeasonAndCompetition`
- `PlayerService`: `findByName`, `findByNationality`, `findByClub`, `getTopPlayers`, `getTopPlayersByClub`
- `StatisticsService`: `getTeamRecord`, `getHomeRecord`, `getHeadToHead`, `getStandings`, `getBiggestWins`, `getAverageGoalsPerMatch`
- `TeamNameNormalizer`: `normalize`, `matches`

## Data schema

- `Match(competition, datetime, homeTeam, awayTeam, homeGoals, awayGoals, season, round, stage)` — record.
- `Player(id, name, age, nationality, club, position, overall, potential)` — record.

Data source: 5 match CSVs (Brasileirao, Copa do Brasil, Libertadores, BR-Football, novo_campeonato) + `fifa_data.csv` under `data/kaggle/`.
