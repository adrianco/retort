# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entrypoint: resolves data dir, loads store, wires tools, runs server | `main()`, `resolveDataDir()` |
| mcp.go | Minimal JSON-RPC 2.0 stdio MCP server (initialize/ping/tools.list/tools.call) | `Server`, `NewServer()`, `(*Server).Run/Register/handle/callTool` |
| tools.go | Registers the 6 MCP tools and their JSON schemas, unmarshals args | `RegisterTools()`, `Tool` |
| queries.go | All query logic (search, H2H, team record, standings, stats, players) | `(*Store).SearchMatches/HeadToHead/TeamRecord/Standings/StatsOverview/SearchPlayers` |
| store.go | In-memory Store, team-name indexing & fuzzy resolution, Match/Player models | `Store`, `Match`, `Player`, `(*Store).resolveTeam/addMatch/addPlayer` |
| load.go | Orchestrates loading all 6 CSVs with cross-source dedup by season cutoff | `LoadStore()`, `seasonRange()`, `loadFile[T]()` |
| loaders.go | Per-file CSV parsers (Brasileirão, Cup, Libertadores, BR-Football, novo, FIFA) | `loadBrasileirao/loadCup/loadLibertadores/loadBRFootball/loadNovoCampeonato/loadFIFA` |
| normalize.go | Team-name parsing, accent folding, state-suffix stripping, key normalization | `parseTeamName()`, `normalizeKey()`, `teamName` |
| parse.go | Flexible value parsers (multi-format dates, int/float/goal loose parsing) | `parseDateFlexible/combineDateTime/parseGoal/parseIntLoose/parseFloatLoose` |
| queries_test.go | Query-layer tests against real dataset (standings, H2H, records, stats) | 9 test functions |
| mcp_test.go | JSON-RPC protocol tests (initialize, tools/list, tools/call, errors) | 6 test functions |
| store_test.go | Store/real-data load & team-resolution tests | 3 test functions |
| loaders_test.go | Per-CSV loader tests (formats, NA handling, date combine) | 5 test functions |
| normalize_test.go | Team-name/normalization unit tests | 4 test functions |

All source is stdlib-only (no `go.sum`, no external dependencies).
