# Interfaces

## MCP tools (stdio server, `ModelContextProtocol` SDK)

| Tool | Category | Purpose | Handler |
|------|----------|---------|---------|
| `search_matches` | Match | Filter matches by team/opponent/competition/season/date range | `MatchTools.cs:SearchMatches` |
| `head_to_head` | Match | Head-to-head W/L/D between two teams | `MatchTools.cs:HeadToHead` |
| `team_record` | Team | W/L/D + goals for/against for a team, by season/competition/home-away | `TeamTools.cs:TeamRecord` |
| `compare_teams` | Team | Compare two teams' records | `TeamTools.cs:CompareTeams` |
| `search_players` | Player | Search FIFA players by (partial) name | `PlayerTools.cs:SearchPlayers` |
| `top_rated_players` | Player | Top players filtered by nationality/club/position | `PlayerTools.cs:TopRatedPlayers` |
| `brazilian_players_at_brazilian_clubs` | Player | Brazilian players grouped by Brazilian club | `PlayerTools.cs:BrazilianPlayersAtBrazilianClubs` |
| `standings` | Competition | Season standings computed from match results | `CompetitionTools.cs:Standings` |
| `average_goals_per_match` | Statistics | Avg goals + home/away/draw win rates | `StatisticsTools.cs:AverageGoalsPerMatch` |
| `best_home_record` | Statistics | Teams ranked by home win rate | `StatisticsTools.cs:BestHomeRecord` |
| `best_away_record` | Statistics | Teams ranked by away win rate | `StatisticsTools.cs:BestAwayRecord` |
| `biggest_wins` | Statistics | Largest goal-margin victories | `StatisticsTools.cs:BiggestWins` |

## Library API (Core, MCP-independent)

- `SoccerDataRepository` — `LoadFromDefaultLocation()`, `LoadFromDirectory(dir)`; exposes loaded matches + players.
- Query services: `MatchQueryService`, `TeamQueryService`, `CompetitionQueryService`, `PlayerQueryService`, `StatisticsService`.
- Helpers: `TeamNameNormalizer`, `FlexibleDateParser`, `CompetitionNameParser`, `ResponseFormatter`, `DataPathResolver`.

## Data schema (in-memory records)

- `MatchRecord`: competition, season, date, home/away team (normalized), home/away goals, stage/round.
- `PlayerRecord`: id, name, nationality, overall, potential, club, position, physical/skill attributes.
- `Competition` enum: Brasileirao, CopaDoBrasil, Libertadores, SerieB, SerieC.
- `StandingsRow`: position, team, played, W, D, L, GF, GA, points.

## Data sources (CSV, `data/kaggle/`)

`Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`, `fifa_data.csv`. Overlapping Série A datasets are de-duplicated by season to avoid double-counting.
