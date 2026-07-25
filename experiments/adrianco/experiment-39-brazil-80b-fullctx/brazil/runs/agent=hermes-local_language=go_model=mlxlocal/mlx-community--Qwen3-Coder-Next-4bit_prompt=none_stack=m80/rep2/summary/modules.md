# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Server struct + CLI dispatch; MCP protocol type defs (unused for serving) | `NewServer`, `Server.Listen`, `Server.LoadData`, `main()` |
| data.go | Match CSV loading (5 per-file parsers), team stats, standings | `MatchDataStore`, `LoadCSV`, `FindMatchesByTeam`, `GetTeamStats`, `GetBrasileiraoStandings`, `normalizeTeamName` |
| player_data.go | FIFA player CSV loading and player queries | `PlayerDataStore`, `LoadCSV`, `SearchPlayers`, `FindPlayersByNationality`, `FindPlayersByClub`, `GetTopBrazilianPlayers` |
| main_test.go | Unit tests over loading + query functions | 10 `Test*` functions |
