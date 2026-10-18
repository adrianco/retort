# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/data.ts | CSV parsing, team-name normalization, date coercion; loads all 6 Kaggle datasets into in-memory `Match[]`/`Player[]` | `SoccerData`, `parseCsv()`, `normalize()`, `matchesName()`, `isoDate()` |
| src/service.ts | Query layer over the loaded data — matches, team stats, head-to-head, standings, players, aggregates | `SoccerService` (`findMatches`, `teamStats`, `headToHead`, `standings`, `players`, `aggregate`) |
| src/server.ts | MCP stdio server: JSON-RPC line loop dispatching `initialize` / `tools/list` / `tools/call` to 6 tools | module entrypoint (`#!/usr/bin/env node`), `call()`, `respond()` |
| test/service.test.ts | `node:test` BDD-style suite over parsing, normalization, data coverage, match/team/player queries, standings | 7 test functions |
