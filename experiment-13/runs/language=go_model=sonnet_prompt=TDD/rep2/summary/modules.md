# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | MCP server bootstrap: loads all CSVs into `Database`, registers 6 tools, serves on stdio | `main()` |
| types.go | Core data types and competition constants | `Match`, `Player`, `TeamStats`, `Standing`, `Database`, `Comp*` |
| loader.go | CSV loaders for the 5 match datasets + FIFA players; date/int/float parsing | `LoadBrasileirao`, `LoadCopa`, `LoadLibertadores`, `LoadBRFootball`, `LoadHistorico`, `LoadFIFA`, `ParseDate` |
| normalizer.go | Team-name normalization (strips `-XX` state suffix) and matching | `NormalizeTeam`, `TeamMatches` |
| queries.go | Match search, head-to-head, team stats, standings computation | `SearchMatches`, `HeadToHead`, `GetTeamStats`, `GetStandings` |
| players.go | FIFA player search/filter | `SearchPlayers` |
| stats.go | Aggregate statistics (avg goals, biggest wins, best home record) | `GetStatistics` |
| tools.go | MCP tool handlers wrapping the query layer, JSON marshaling | `HandleSearchMatches`, `HandleHeadToHead`, `HandleTeamStats`, `HandleStandings`, `HandleSearchPlayers`, `HandleGetStatistics` |
| loader_test.go | CSV loader row-count and parse tests | 11 test functions |
| normalizer_test.go | Normalize/match + date parsing tests | 6 test functions |
| queries_test.go | Search, H2H, team-stats, standings tests | 7 test functions |
| players_test.go | Player search filter tests | 6 test functions |
| stats_test.go | Aggregate statistics tests | 4 test functions |
