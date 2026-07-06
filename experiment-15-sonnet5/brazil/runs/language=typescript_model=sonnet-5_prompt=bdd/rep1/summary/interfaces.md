# Interfaces

## MCP tools (registered in `src/server.ts`)

| Tool | Purpose | Query |
|------|---------|-------|
| search_matches | Matches by team/opponent/competition/season/date range | `matches.ts:searchMatches` |
| head_to_head | Tally W/D/L between two teams | `matches.ts:headToHead` |
| most_recent_match | Latest match between two teams | `matches.ts:mostRecentMatch` |
| team_record | W/D/L, goals for/against, win rate for a team | `teams.ts:getTeamRecord` |
| team_competitions | Distinct competitions a team appears in | `teams.ts:competitionsForTeam` |
| rank_teams | Rank teams by win rate / goals / goal diff | `teams.ts:rankTeamsByRecord` |
| search_players | FIFA players by name/nationality/club/position | `players.ts:searchPlayers` |
| brazilian_players_by_club | Brazilian players grouped by Brazilian club + avg rating | `players.ts:brazilianPlayersAtBrazilianClubs` |
| standings | League table computed from match results | `competitions.ts:calculateStandings` |
| relegation_zone | Bottom N of calculated table (relegation proxy) | `competitions.ts:bottomOfTable` |
| seasons_for_competition | Seasons with data for a competition | `competitions.ts:seasonsForCompetition` |
| goal_stats | Avg goals/match, home/away win rate, draw rate | `stats.ts:calculateGoalStats` |
| biggest_wins | Largest goal-difference victories | `stats.ts:biggestWins` |

Transport: stdio (`StdioServerTransport`). Competition enum: `Brasileirao | CopaDoBrasil | Libertadores | Other`.

## Data schema (in-memory)

- **Match**: competition, sourceLabel, date, season, round/stage, home/away team (+key/state), home/away goals, venue, extra stats, sourceFile.
- **Player**: id, name, age, nationality, overall, potential, club (+key), position, jersey, height, weight, wage, value.

## Data sources (`data/kaggle/`)

Brasileirao_Matches.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, novo_campeonato_brasileiro.csv, BR-Football-Dataset.csv, fifa_data.csv. Overlapping seasons deduplicated via primary/secondary source designation.

## Tests

teams(8), matches(9), players(7), competitions(6), stats(5), store(6), normalize(15), server(9) — 65 total, all Given/When/Then style.
