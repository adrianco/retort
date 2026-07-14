# Interfaces

## MCP tools (registered in `src/server.ts`)

| Tool | Inputs | Backing function |
|------|--------|------------------|
| find_matches | team?, opponent?, competition?, season?, dateFrom?, dateTo?, limit? | `matchQueries.ts:findMatches` |
| head_to_head | teamA, teamB, competition?, season?, limit? | `matchQueries.ts:headToHead` |
| team_record | team, competition?, season?, venue? | `teamQueries.ts:teamRecord` |
| team_competitions | team | `teamQueries.ts:teamCompetitions` |
| standings | competition, season | `competitionQueries.ts:standings` |
| list_competitions | (none) | `competitionQueries.ts:listCompetitions` |
| average_goals | competition?, season? | `statsQueries.ts:averageGoals` |
| biggest_wins | competition?, season?, limit? | `statsQueries.ts:biggestWins` |
| best_venue_record | venue, competition?, season?, minMatches?, limit? | `statsQueries.ts:bestVenueRecord` |
| search_players | name?, nationality?, club?, position?, limit? | `playerQueries.ts:searchPlayers` |
| players_by_club | club, limit? | `playerQueries.ts:playersByClub` |
| brazilian_players_by_club | clubs[] | `playerQueries.ts:brazilianPlayersByClub` |

Transport: MCP over stdio (`StdioServerTransport`). Input schemas declared with `zod`.

## Data schema (in-memory, `src/types.ts`)

- `Match`: id, source, competition, season, round, stage, date, dateRaw, homeTeam (`TeamKey`), awayTeam (`TeamKey`), homeGoals, awayGoals, stadium, extra (`MatchExtraStats`: corners/shots/attacks).
- `Player`: id, name, age, nationality, overall, potential, club, position, jerseyNumber, preferredFoot, height, weight, valueRaw, wageRaw.
- `Dataset`: `{ matches: Match[]; players: Player[] }`, built once from 6 CSVs and cached.

## Data sources (CSV, `data/kaggle/`)

Brasileirao_Matches.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, BR-Football-Dataset.csv, novo_campeonato_brasileiro.csv, fifa_data.csv. Loaded and deduped (historical Brasileirao fills only uncovered seasons; BR-Football Serie A/Copa do Brasil rows dropped where already covered).

## HTTP routes / CLI commands

(none) — this is a stdio MCP server, not an HTTP or CLI app.
