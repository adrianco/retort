# Interfaces

## MCP tools (the public surface)

| Tool | Inputs | Returns | Handler |
|------|--------|---------|---------|
| `find_matches` | team, opponent, homeTeam, awayTeam, competition, stage, season, dateFrom, dateTo, limit | `{count, returned, matches[], summary}` | `server.ts` → `DataStore.findMatches` |
| `head_to_head` | team1, team2, competition?, season? | `{team1, team2, totalMatches, team1Wins, team2Wins, draws, team1Goals, team2Goals, matches[], summary}` | `server.ts` → `DataStore.headToHead` |
| `team_record` | team, season?, competition?, venue(home/away/all)? | `{team, matches, wins, draws, losses, goalsFor, goalsAgainst, points, winRate, summary}` | `server.ts` → `DataStore.teamRecord` |
| `find_players` | name, nationality, club, position, minOverall, sortBy(overall/potential/age/name), limit | `{count, returned, players[], summary}` | `server.ts` → `DataStore.findPlayers` |
| `competition_standings` | competition, season | `{competition, season, teams, champion, standings[], summary}` | `server.ts` → `DataStore.standings` |
| `competition_statistics` | competition?, season? | `{matches, totalGoals, averageGoalsPerMatch, homeWins, awayWins, draws, homeWinRate, awayWinRate, drawRate, biggestWins[], summary}` | `server.ts` → `DataStore.competitionStatistics` |
| `dataset_summary` | (none) | `{totalMatches, totalPlayers, competitions[], seasonsFrom, seasonsTo, summary}` | `server.ts` → DataStore introspection |

Transport: MCP `StdioServerTransport` (production), `InMemoryTransport` (tests). Every result carries both a `text` content block and `structuredContent`.

## CLI commands

`node dist/index.js` (or `npm start` / `npm run dev`) — boots the stdio MCP server. Data dir resolved from `$BRAZILIAN_SOCCER_DATA_DIR`, then `./data/kaggle`, then relative to the bundle.

## Data schema (in-memory)

- **Match**: competition, season, date (ISO), round?, homeTeam, awayTeam, homeState?, awayState?, homeGoals, awayGoals, stadium?
- **Player**: id, name, age?, nationality?, overall?, potential?, club?, position?, jerseyNumber?

Sourced from 6 Kaggle CSVs (5 match files → `Match`, `fifa_data.csv` → `Player`).
