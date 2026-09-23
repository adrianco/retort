# Interfaces

## MCP tools (stdio transport, `McpServer` from `@modelcontextprotocol/sdk`)

| Tool | Purpose | Handler |
|------|---------|---------|
| search_matches | Matches by team, opponent, venue, competition, season, date range, stage | `tools.ts:search_matches` → `queries.ts:findMatches` |
| head_to_head | Head-to-head record + match list between two teams | `tools.ts:head_to_head` → `queries.ts:headToHead` |
| team_stats | W/D/L and goals for/against for a team (season/competition/venue) | `tools.ts:team_stats` → `queries.ts:teamRecord` |
| standings | League table for a season, computed from results (champion/relegation marked) | `tools.ts:standings` → `queries.ts:standings` |
| competition_stats | Avg goals/match, home/away/draw rates, top scoring teams | `tools.ts:competition_stats` → `queries.ts:competitionStats` |
| biggest_wins | Largest victory margins | `tools.ts:biggest_wins` → `queries.ts:biggestWins` |
| best_records | Best home/away records by points-per-game | `tools.ts:best_records` → `queries.ts:bestRecords` |
| team_competitions | Competitions/seasons a team appears in | `tools.ts:team_competitions` → `queries.ts:teamCompetitions` |
| derbies | Traditional derby matches (Fla-Flu, Grenal, ...) | `tools.ts:derbies` → `queries.ts:derbies` |
| search_players | FIFA players by name/nationality/club/position/minOverall | `tools.ts:search_players` → `queries.ts:searchPlayers` |
| get_player | Detailed player profile by name | `tools.ts:get_player` → `queries.ts:searchPlayers`/`playerDetail` |
| brazilian_club_players | FIFA players at Brasileirão clubs (cross-file) | `tools.ts:brazilian_club_players` → `queries.ts:brazilianClubPlayers` |
| team_profile | Cross-dataset: record + competitions + FIFA players | `tools.ts:team_profile` |
| dataset_info | Loaded datasets + row counts | `tools.ts:dataset_info` |

(`TOOL_SCHEMAS` also lists `team_stats` venue enum; 14 distinct handlers registered in a loop.)

## Data schema (in-memory, loaded from CSV)

- **Match**: `date` (YYYY-MM-DD), `season`, `competition` (enum), `round?`, `home`/`away` (display), `homeKey`/`awayKey` (normalized), `homeGoals`/`awayGoals`, `arena?`, `stats?` (corners/shots/attacks), `source`.
- **Player**: `id`, `name`, `age`, `nationality`, `overall`, `potential`, `club`, `position`, `jerseyNumber`, `height`, `weight`, `preferredFoot`, `value`, `wage`, `skills` (34 FIFA attributes).
- **Dataset**: `matches[]`, `players[]`, `serieA` (Map season→authoritative match list), `fileCounts`.

## HTTP routes / CLI commands

(none) — the server speaks MCP over stdio only; `server.ts` is executable (`#!/usr/bin/env node`, `bin` entry) but takes no CLI subcommands.
