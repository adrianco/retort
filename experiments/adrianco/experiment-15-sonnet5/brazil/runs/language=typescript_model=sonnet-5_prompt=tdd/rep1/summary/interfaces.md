# Interfaces

## HTTP routes

(none) — this is an MCP server over stdio, not HTTP.

## MCP tools

Registered in `src/server.ts` via `server.registerTool`; handlers in `src/tools.ts`. All return `{ content: [{ type: "text", text }] }`.

| Tool | Input schema | Returns | Handler |
|------|--------------|---------|---------|
| search_matches | team, opponent?, competition?, season?, startDate?, endDate?, limit? | Text list of matches for a team + optional head-to-head line | `tools.ts:searchMatchesTool` |
| team_record | team, competition?, season?, venue?(home\|away\|all) | Text W/D/L record, goals for/against, win rate | `tools.ts:teamRecordTool` |
| compare_teams | teamA, teamB, competition?, season? | Text head-to-head + each team's overall record | `tools.ts:compareTeamsTool` |
| search_players | name?, nationality?, club?, position?, limit? | Text ranked player list (by overall) | `tools.ts:searchPlayersTool` |
| competition_standings | competition, season | Text ordered standings table (pts, W/D/L, GD) | `tools.ts:competitionStandingsTool` |
| dataset_statistics | competition?, season? | Text avg goals/match, home/away/draw rates, biggest wins | `tools.ts:datasetStatisticsTool` |
| player_club_context | name | Text player info + their club's match record (cross-file) | `tools.ts:playerClubContextTool` |
| list_team_competitions | team | Text list of distinct competitions the team appears in | `tools.ts:listTeamCompetitionsTool` |

## CLI commands

`src/index.ts` runs as an executable (`#!/usr/bin/env node`). No subcommands or flags. Data directory is read from env var `BRAZILIAN_SOCCER_DATA_DIR`, defaulting to `../data/kaggle`.

## Library API (exported functions/types)

- Match layer: `findMatchesByTeam`, `headToHead`, `canonicalMatches`
- Team layer: `teamRecord`, `compareTeams`
- Player layer: `searchPlayersByName`, `findPlayersByClub`, `findPlayersByNationality`, `topRatedPlayers`
- Competition/stats: `calculateStandings`, `averageGoalsPerMatch`, `homeAwayWinRates`, `biggestWins`
- Normalization: `normalizeTeamName`, `teamKey`, `teamsMatch`, `canonicalizeTeamNames`, `splitStateSuffix`, `stripAccents`
- Parsing: `parseCSV`, `parseFlexibleDate`, `formatISODate`, per-file CSV parsers, `loadAllData`
- Server: `createServer`

## Data schema

Internal domain types (`src/types.ts`); data is loaded from CSV into memory, no database.

`Match`: id, source, competition, date (Date), season (number), round?, stage?, homeTeam, awayTeam, homeTeamState?, awayTeamState?, homeGoals, awayGoals, venue?, extra? (record of match stats, e.g. corners/shots from BR-Football-Dataset).

`Player`: id, name, age?, nationality, club, overall?, potential?, position?, jerseyNumber?, height?, weight?.

### Source CSVs (parsed by `dataLoader.ts`)

| File | Competition assigned | Notes |
|------|---------------------|-------|
| Brasileirao_Matches.csv | Brasileirão | round field |
| Brazilian_Cup_Matches.csv | Copa do Brasil | state suffix split from team name |
| Libertadores_Matches.csv | Copa Libertadores | stage field |
| BR-Football-Dataset.csv | from `tournament` column | extra stats; season derived from date year |
| novo_campeonato_brasileiro.csv | Brasileirão | Brazilian date format, arena as venue |
| fifa_data.csv | (players) | FIFA player attributes |
