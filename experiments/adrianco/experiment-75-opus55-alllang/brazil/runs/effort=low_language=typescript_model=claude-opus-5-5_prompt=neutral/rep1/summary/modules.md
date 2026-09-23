# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/server.ts | MCP server entrypoint: stdio transport, Zod tool schemas, registers 15 tools | `buildServer()`, `TOOL_SCHEMAS` |
| src/tools.ts | Text-formatting tool handlers over the query layer (transport-agnostic, unit-testable) | `createHandlers(ds)` |
| src/queries.ts | Query/analytics engine: match search, records, standings, head-to-head, stats, derbies, player search | `findMatches`, `teamRecord`, `standings`, `headToHead`, `competitionStats`, `biggestWins`, `bestRecords`, `searchPlayers`, `brazilianClubPlayers`, `RIVALRIES` |
| src/data.ts | Dataset loader: parses all 6 CSVs into typed `Match`/`Player`, builds authoritative per-season Série A index | `loadDataset()`, `defaultDataDir()`, `Match`, `Player`, `Dataset`, `Competition` |
| src/normalize.ts | Team-name normalization, accent stripping, multi-format date parsing, fuzzy team matching | `normalizeTeam`, `displayTeam`, `stripAccents`, `parseDate`, `teamMatches` |
| src/csv.ts | Minimal RFC-4180 CSV parser (quoted fields, escaped quotes) | `parseCsv()` |
| tests/soccer.test.ts | Vitest BDD suite over loader, normalization, and all query features | 33 `it`/`it.each` blocks (47 expanded cases) |
