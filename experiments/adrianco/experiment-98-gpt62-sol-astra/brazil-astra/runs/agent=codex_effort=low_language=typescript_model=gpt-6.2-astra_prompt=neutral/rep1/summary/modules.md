# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| data.ts | CSV reader, team-name normalization, date parsing, and the `Graph` that loads+dedupes all match/player datasets | `Graph`, `club()`, `fold()`, `day()`, `league()`, `files`, `Match` |
| queries.ts | MCP tool definitions (JSON schemas) and the `query()` engine for matches/records/statistics/players | `tools`, `query()` |
| server.ts | Hand-rolled MCP JSON-RPC 2.0 server over stdio (initialize/ping/tools/list/tools/call) | top-level stdin loop, `respond()` |
| soccer.test.ts | node:test suite: dataset counts, standings, derbies, stages, stats, stdio protocol, 20 sample-question cases | 7 named tests + 20 parameterized example tests |
| package.json | Build (`tsc`) + test (`node --test`) scripts; deps: typescript, @types/node | — |
| tsconfig.json | NodeNext, ES2022, strict | — |
| README.md | Usage/architecture notes | — |
