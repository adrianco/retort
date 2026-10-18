# Architecture Summary

> `run-summary` skill is not invocable from this harness's skill list; this is a hand-written stand-in covering modules, interfaces, and flow.

## Overview

A TypeScript MCP (Model Context Protocol) server over six provided Kaggle CSVs of
Brazilian soccer data. Layered as: CSV parsing → typed loading/dedupe → pure query
functions → MCP tool registration → stdio entrypoint. The query layer is transport-free
so it is unit-testable; the tool layer is thin.

## Modules

| File | Responsibility |
|------|----------------|
| `src/csv.ts` | Streaming-ish CSV record parser (`parseCsvRecords`). |
| `src/normalize.ts` | Team-name and competition canonicalization, accent folding (`normalizeTeam`, `normalizeCompetition`, `teamMatches`, `foldText`), date/number parsing. |
| `src/types.ts` | `Dataset`, `Match`, `Player`, `MatchFilter` shapes. |
| `src/loader.ts` | Reads all 6 CSVs, maps each to `Match`/`Player`, source-prioritizes overlapping Brasileirão files, cross-file dedupe, team-state inference; caches per dir. |
| `src/queries.ts` | Pure query functions: `filterMatches`, `teamRecord`, `headToHead`, `standings`, `rankTeams`, `leagueStats`, `biggestWins`, `searchPlayers`, `clubSummary`, `teamProfile`. |
| `src/format.ts` | Text formatting of query results into spec-shaped answers. |
| `src/tools.ts` | Registers 11 MCP tools on `McpServer`, each zod-validated, delegating to a query. |
| `src/index.ts` | Stdio entrypoint; loads dataset once, connects `StdioServerTransport`. |

## Interfaces (MCP tools)

`search_matches`, `team_record`, `head_to_head`, `standings`, `rank_teams`,
`league_stats`, `biggest_wins`, `search_players`, `team_profile`, `club_summary`,
`dataset_info`.

## Flow

`index.ts` → `getDataset()` (loader reads `data/kaggle/*.csv`, dedupes, caches) →
`createServer(dataset)` registers tools → each tool call validates args with zod,
calls the matching pure query over the in-memory `Dataset`, formats text, returns.

## Data handling notes

- Source prioritization avoids double-counting the overlapping Brasileirão files, so
  computed standings match published points (2019: Flamengo 90, Santos/Palmeiras 74 —
  asserted in `test/loader.test.ts`).
- Team names normalized across state-suffix variants ("Palmeiras-SP" vs "Palmeiras");
  accent-insensitive matching for players and clubs.
- Cross-file dedupe keys on (sorted team pair, score, date within 1 day).
