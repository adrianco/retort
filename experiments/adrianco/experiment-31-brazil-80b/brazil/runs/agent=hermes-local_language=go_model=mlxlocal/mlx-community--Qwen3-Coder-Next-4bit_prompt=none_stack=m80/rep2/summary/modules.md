# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | "MCP server" struct + tool-shaped handlers; wires DataLoader → QueryHandler; `Run()` logs tool list | `Server`, `NewServer()`, `Handle*` (10 methods), `main()` |
| data/loader.go | Loads the 5 match CSVs + FIFA players; team-name normalization; date parsing; filter helpers | `DataLoader`, `NewDataLoader()`, `LoadAll()`, `GetMatches()`, `GetPlayers()` |
| query/handler.go | Query engine over loaded data: match/player search, team stats, standings, H2H, biggest wins; response formatters | `QueryHandler`, `NewQueryHandler()`, `SearchMatches`, `GetTeamStats`, `GetTeamHeadToHead`, `SearchPlayers`, `CalculateStandings` |
| model/match.go | Data structs shared across packages | `Match`, `Player`, `TeamStats`, `TeamHeadToHead`, `CompetitionStandings`, `BigWin` |
| data/loader_test.go | Loader + filter unit tests | 14 test functions |
| query/handler_test.go | Query-engine unit tests | 18 test functions |
