# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | CLI entry point; loads CSVs into the DB and serves over MCP stdio | `main()` (shebang bin) |
| src/server.ts | MCP server wiring; registers tools, stdio transport | `buildServer()`, `runStdio()`, `SERVER_INFO` |
| src/tools.ts | Tool registry: 8 MCP tools mapping args → formatted answers | `createTools()`, `ToolDef` |
| src/database.ts | In-memory query engine over matches + players | `SoccerDatabase`, `MatchQuery`, `Statistics` |
| src/loader.ts | Per-dataset CSV parsers + canonicalization | `loadAll()`, `parseBrasileirao()`, `parseCup()`, `parseLibertadores()`, `parseBRFootball()`, `parseNovoBrasileirao()`, `parsePlayers()`, `canonicalMatches()` |
| src/normalize.ts | Team-name / date normalization helpers | `normalizeTeamName()`, `normalizeName()`, `teamMatches()`, `parseDate()`, `formatDate()`, `removeAccents()` |
| src/format.ts | Human-readable result formatters | `formatMatch()`, `formatMatchList()`, `formatHeadToHead()`, `formatTeamRecord()`, `formatStandings()`, `formatStatistics()`, `formatPlayerList()` |
| src/types.ts | Core domain types | `Match`, `Player`, `TeamRecord`, `MatchStats`, `Competition` |
| tests/loader.test.ts | CSV parsing + canonicalization unit tests | 14 test cases |
| tests/normalize.test.ts | Name/date normalization unit tests | 20 test cases |
| tests/database.test.ts | Query-engine unit tests | 18 test cases |
| tests/tools.test.ts | Tool handler unit tests | 11 test cases |
| tests/format.test.ts | Formatter unit tests | 11 test cases |
| tests/server.test.ts | MCP server registration tests | 4 test cases |
| tests/integration.test.ts | End-to-end over real bundled datasets | 11 test cases |
