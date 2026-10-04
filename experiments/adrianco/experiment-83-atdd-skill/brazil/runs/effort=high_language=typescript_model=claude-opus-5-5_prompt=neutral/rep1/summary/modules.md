# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Executable entry point; loads data and serves over stdio | `main()` |
| src/server.ts | MCP server wiring; registers every tool on an `McpServer` | `createServer()` |
| src/tools.ts | Declarative tool table (name/title/description/zod schema/handler) and dispatcher | `TOOLS`, `runTool()` |
| src/query.ts | Query engine over the loaded dataset (matches, teams, players, standings, stats) | `SoccerQueries`, `QueryError`, `parseCompetition()` |
| src/data.ts | Loads the six Kaggle CSVs, merges duplicate fixtures, builds the in-memory graph | `loadDataset()`, `getDataset()`, `Match`, `Player`, `Dataset` |
| src/teams.ts | Team-name registry: normalisation, fuzzy resolution, derby detection | `TeamRegistry`, `derbyName()`, `Team` |
| src/normalize.ts | Text folding (accents), multi-format date parsing, numeric coercion | `foldText()`, `parseDate()`, `parseIntOrNull()`, `parseNum()`, `daysBetween()` |
| src/csv.ts | Minimal CSV reader (quoted fields, header row) | `readCsvFile()` |
| src/format.ts | Turns query results into human-readable tool text | formatting helpers |
| tests/mcp.test.ts | MCP-protocol integration tests via in-memory client/server | 7 tests |
| tests/sample-questions.test.ts | 27 spec sample questions (Q1–Q27) exercised end-to-end | 27 tests |
| tests/teams.test.ts | Team normalisation/resolution/derby tests | 9 tests |
| tests/data.test.ts | Dataset loading & merge invariants | 9 tests |
| tests/normalize.test.ts | Date/text/number normalisation tests | 6 tests |
| tests/csv.test.ts | CSV parser tests | 3 tests |
| tests/performance.test.ts | Latency budgets (<2s lookups, <5s aggregates) | 1 + parametrised |
| tests/helpers.ts | Shared `ask()` test helper | (helper, no tests) |
