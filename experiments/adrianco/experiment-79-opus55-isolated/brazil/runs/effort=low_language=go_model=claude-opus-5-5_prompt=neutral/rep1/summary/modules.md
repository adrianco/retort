# Modules

The project is a single Go package (`package main`, module `brsoccer`) with no
internal sub-packages. Source files are flat in the run directory.

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entry: locate data dir, load store, serve MCP over stdio or run one tool with `-call` | `main()`, `findDataDir()` |
| mcp.go | Minimal JSON-RPC 2.0 MCP server over newline-delimited stdio (initialize, ping, tools/list, tools/call) | `Server`, `NewServer()`, `Serve()`, `HandleMessage()`, `CallTool()`, `Tool`, `Args` |
| data.go | Loads the six Kaggle CSVs into an in-memory `Store`, de-duplicates/merges overlapping match sources, loads FIFA players | `Store`, `Match`, `Player`, `LoadStore()`, `FileInfo`, `ExtStats` |
| normalize.go | Team-name normalisation: fold accents, strip generic tokens, resolve (base, state) keys, aliases, specials, derbies registry | `Registry`, `Team`, `NewRegistry()`, `parseName()`, `fold()`, `Find()`, `Freeze()` |
| queries.go | Query layer: match filtering, W/D/L records, standings, rankings, summaries, biggest wins, derbies, player search | `Filter`, `Record`, `TeamRow`, `Summary`, `FindMatches()`, `Standings()`, `Rankings()`, `SearchPlayers()`, `ResolveCompetition()` |
| tools.go | 15 MCP tool definitions: argument parsing, schema builders and text formatting on top of the query layer | `buildTools()`, `toolSearchMatches()`, `toolHeadToHead()`, `toolTeamStats()`, ... `toolDatasetInfo()` |
| soccer_test.go | BDD-style feature tests exercising loading, normalisation, queries and the MCP protocol | 10 `TestFeature_*` functions + helpers (`givenTheDataIsLoaded`, `call`, `rpc`, `mustContain`) |

Notes:
- `go.mod` declares module `brsoccer` (Go, no external dependencies — standard
  library only).
- Non-source files present but not summarized: `TASK.md`, `README.md`,
  `brazilian-soccer-mcp-guide.md`, `prompts.txt`, `data/` (CSV inputs),
  agent logs and scoring artifacts.
