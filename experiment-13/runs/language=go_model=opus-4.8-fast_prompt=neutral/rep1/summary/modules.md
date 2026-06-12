# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entry: parses flags, loads data, registers tools, serves MCP over stdio (or runs `-demo`) | `main()`, `runDemo()`, `logLoadReport()` |
| tools.go | Wires 12 MCP tools to `soccer.Store` query methods, with inline JSON-Schema | `registerTools()`, `parseVenue()`, `unmarshal()` |
| mcp/server.go | Dependency-free MCP server over newline-delimited JSON-RPC 2.0 (stdio): handshake, tools/list, tools/call, ping | `Server`, `Tool`, `ToolHandler`, `NewServer()`, `(*Server).AddTool`, `(*Server).Serve`, `ProtocolVersion` |
| soccer/models.go | Unified `Match` + `Player` data model; canonical competition name constants | `Match`, `Player`, `(Match).Winner`, `(Match).Margin`, `CompSerieA`/`CompSerieB`/`CompSerieC`/`CompCopaBrasil`/`CompLibertadores` |
| soccer/loader.go | CSV ingestion: per-file loaders for all 6 datasets, normalized into the unified model; date/int parsing | `LoadAll()`, `LoadReport`, `FileReport` |
| soccer/store.go | In-memory knowledge graph: team-key resolution, de-duplication, low-level match/player primitives | `Store`, `LoadEmptyForTest()`, `(*Store).ResolveTeam`, `(*Store).FindMatches`, `(*Store).FindMatchesClean`, `(*Store).FindPlayers`, `(*Store).Display`, `(*Store).Competitions`, `(*Store).SeasonRange`, `MatchFilter`, `PlayerFilter`, `CleanBySource()` |
| soccer/queries.go | High-level query API: resolves fuzzy names, runs analysis, returns formatted LLM-ready answer strings | `MatchQuery`, `(*Store).SearchMatches`, `HeadToHeadQuery`, `TeamRecordQuery`, `TeamCompetitionsQuery`, `StandingsQuery`, `CompetitionStatsQuery`, `BiggestWinsQuery`, `TopScoringTeamsQuery`, `SearchPlayersQuery`, `PlayerInfoQuery`, `ClubPlayersQuery`, `DatasetOverview`, `ResolveCompetition()` |
| soccer/stats.go | Pure aggregate analysis over match slices (records, head-to-head, standings, summaries) | `Record`, `H2H`, `CompetitionStats`, `Venue`, `TeamRecord()`, `HeadToHead()`, `Standings()`, `Summarize()`, `BiggestWins()`, `TopScoringTeams()` |
| soccer/format.go | Human-readable rendering of matches, records, standings, player lists | `FormatMatch()`, `FormatMatchList()`, `FormatRecord()`, `FormatStandings()`, `FormatPlayer()`, `FormatPlayerList()` |
| soccer/normalize.go | Team/name normalization: accent folding, base/state splitting, key generation, club aliases | `FoldAccents()`, `NormalizeName()`, `NormalizeTeam()`, `DisplayTeam()` |
| main_test.go | Tool-registration and demo smoke tests | 2 test functions |
| mcp/server_test.go | JSON-RPC protocol / handshake / tool-call tests | 8 test functions |
| soccer/store_test.go | Store resolution + dedup + filter tests | 6 test functions |
| soccer/normalize_test.go | Normalization / key-splitting tests | 4 test functions |
| soccer/integration_test.go | End-to-end query tests over loaded data | 8 test functions |
| soccer/stats_test.go | Pure analysis-function tests | 5 test functions |
