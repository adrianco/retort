# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | MCP stdio entrypoint — loads data, starts server | top-level `await createServer(loadDataset()).connect(...)` |
| src/server.ts | Builds the MCP server, registers 14 tools with zod schemas | `createServer(ds)` |
| src/queries.ts | Query/analytics layer over the dataset (matches, teams, players, standings, stats) | `filterMatches`, `searchMatches`, `headToHead`, `teamRecord`, `standings`, `competitionStats`, `biggestWins`, `bestRecord`, `searchPlayers`, `datasetInfo`, … |
| src/data.ts | CSV loading, parsing, dedup, per-season league table source selection | `loadDataset`, `parseDate`, `Match`, `Player`, `Dataset` |
| src/teams.ts | Team-name normalisation, display names, derby pairs | `teamKey`, `displayName`, `registerDisplay`, `stripAccents`, `DERBIES` |
| test/acceptance/soccer-knowledge.spec.ts | Executable specs in domain language | 24 `it(...)` cases across 6 describe groups |
| test/dsl/SoccerDsl.ts | DSL: domain vocabulary, delegates to driver | `SoccerDsl` |
| test/drivers/McpSoccerDriver.ts | Protocol driver — only layer aware of MCP/stdio | `McpSoccerDriver` |

(generated source only; `node_modules`, lock files and build artifacts excluded)
