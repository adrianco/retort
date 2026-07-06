# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| cmd/server/main.go | Command entry point; loads datasets from `-data-dir` and serves the MCP server over stdio | `main()` |
| internal/mcpserver/server.go | Registers 7 MCP tools mapping tool args to `soccer.Store` queries | `New(store)`, `textResult()`, `errorResult()` |
| internal/mcpserver/format.go | Renders query results into human-readable text for LLM output | `FormatMatch`, `FormatMatches`, `FormatHeadToHead`, `FormatTeamRecord`, `FormatStandings`, `FormatStatsSummary`, `FormatPlayers` |
| internal/soccer/store.go | In-memory query engine over matches/players (find, head-to-head, records, standings, biggest wins, stats) | `Store`, `NewStore`, `MatchFilter`, `FindMatches`, `HeadToHead`, `TeamRecord`, `Standings`, `BiggestWins`, `StatsSummary` |
| internal/soccer/match.go | `Match` model and per-CSV match loaders/parsers | `Match`, `Outcome()`, `LoadBrasileiraoMatches`, `LoadCopaDoBrasilMatches`, `LoadLibertadoresMatches`, `LoadBRFootballMatches`, `LoadHistoricalBrasileiraoMatches` |
| internal/soccer/player.go | `Player` model and FIFA CSV loader | `Player`, `LoadFIFAPlayers` |
| internal/soccer/player_query.go | Player search/filter logic | `PlayerFilter`, `SearchPlayers` |
| internal/soccer/load.go | Orchestrates loading all six CSVs into a `Store` | `LoadStoreFromDir` |
| internal/soccer/normalize.go | Team-name normalization (accents, state suffixes, aliases) | `NormalizeTeamKey` |
| internal/soccer/date.go | Multi-format date parsing | `ParseDate` |
| internal/soccer/store_test.go | Store query unit tests | 18 test functions |
| internal/soccer/match_test.go | Match loader/parser tests | 6 test functions |
| internal/soccer/load_test.go | Full-directory load integration test | 1 test function |
| internal/soccer/date_test.go | Date parsing tests | 2 test functions |
| internal/soccer/normalize_test.go | Team-name normalization tests | 2 test functions |
| internal/soccer/player_test.go | Player loader/query tests | 1 test function |
| internal/mcpserver/format_test.go | Formatter output tests | 9 test functions |
| internal/mcpserver/server_test.go | MCP server construction/tool test | 1 test function |
