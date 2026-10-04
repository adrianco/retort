# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/server.ts | MCP server (stdio transport); registers every tool | `createServer()` |
| src/tools.ts | 15 MCP tool definitions + text rendering | `tools`, `callTool()`, `formatMatch()`, `compactYears()` |
| src/queries.ts | Query/aggregation layer over the dataset | `SoccerKB`, `resolveCompetition()`, `UnknownEntityError` |
| src/data.ts | Loads & de-duplicates the six Kaggle CSVs into one dataset | `loadDataset()`, `COMPETITIONS`, `Match`, `Player`, `Dataset` |
| src/teams.ts | Team-name normalization + registry, name folding | `TeamRegistry`, `fold()`, `parseTeamName()` |
| src/csv.ts | Minimal CSV parser | `parseCsv()` |
| tests/data.test.ts | Dataset loading + CSV parsing tests | 6 cases |
| tests/queries.test.ts | Query-layer behaviour tests | 21 cases |
| tests/normalization.test.ts | Team/name folding tests | 6 cases |
| tests/server.test.ts | Tool registration + tool-output tests | 8 cases |
| tests/helpers.ts | Shared test fixtures | (helpers) |

(Grouped `it()`/`test()` blocks expand at runtime to 88 executed cases.)
