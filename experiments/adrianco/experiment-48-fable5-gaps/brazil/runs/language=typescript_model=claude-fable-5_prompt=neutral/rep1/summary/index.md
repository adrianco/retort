# Architecture summary — brazilian-soccer-mcp (typescript, claude-fable-5, rep1)

> `run-summary` skill was not available in this environment; this is a hand-written
> architecture note produced during evaluation.

## Modules

| File | LOC | Role |
|------|-----|------|
| `src/index.ts` | 51 | Entry point. Locates `data/kaggle`, loads the dataset, serves the MCP tools over stdio (`StdioServerTransport`). |
| `src/server.ts` | 356 | `createServer(ds)` builds a `McpServer` and registers **11 tools** (search_matches, head_to_head, team_stats, league_standings, search_players, player_profile, competition_stats, biggest_wins, best_records, team_competitions, data_summary). Formatting/presentation lives here. |
| `src/queries.ts` | 458 | The query engine: `filterMatches`, `headToHead`, `teamStats`, `standings`, `searchPlayers`, `competitionStats`, `biggestWins`, `bestRecords`, `teamCompetitions`, plus `resolveCompetition` fuzzy matching. |
| `src/loader.ts` | 290 | Reads all six Kaggle CSVs, normalizes rows into a unified `Match`/`Player` model, and **deduplicates matches across files** (±1 day tolerance) merging extended stats into authoritative fixtures. |
| `src/teams.ts` | 187 | Team-name normalization (strip state suffix, diacritics, aliases) so "Flamengo" matches "Flamengo-RJ". |
| `src/csv.ts` | 73 | A small UTF-8 CSV parser (quoted fields, header map). |
| `src/types.ts` | 64 | `Match`, `Player`, `Dataset`, `Competition` type definitions. |

## Data flow

```
data/kaggle/*.csv → loader.loadDataset() → Dataset{matches[], players[]}
                                             │
                              createServer(ds) registers tools
                                             │
   MCP client ⇄ stdio/InMemory transport ⇄ tool handler → queries.* → formatted text
```

Transport wiring is deliberately split from tool registration (`index.ts` vs
`server.ts`) so tests attach an in-memory transport and exercise the real MCP
protocol rather than calling functions directly.

## Test layout

`tests/` holds 9 vitest BDD-style files (loading, matches, teams, players,
stats, performance, server integration, sample-questions). `sample-questions.test.ts`
parametrizes 24 spec example questions through the live MCP client; `server.test.ts`
verifies tool discovery and end-to-end tool calls over the SDK transport.
`test_coverage=1.0` — the build compiles and every test passes.
