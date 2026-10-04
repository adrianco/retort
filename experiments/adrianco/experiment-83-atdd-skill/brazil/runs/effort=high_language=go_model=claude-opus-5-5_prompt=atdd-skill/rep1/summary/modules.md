# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry point; wires stdin/stdout to the app | `main()` |
| internal/app/app.go | Loads datasets, builds MCP server, registers tools | `Run()`, `version`, `instructions` |
| internal/app/tools.go | Declares the 20 MCP tools and their input schemas; maps tool calls to store queries | `tools()`, `handlers` |
| internal/mcpserver/server.go | Minimal JSON-RPC 2.0 MCP server over line-delimited stdio | `Server`, `New()`, `AddTool()`, `Serve()` |
| internal/mcpserver/args.go | Lenient argument coercion (numbers-as-strings etc.) | `Args`, `String()`, `Int()`, `Ints()` |
| internal/soccer/load.go | Reads the six Kaggle CSVs; parses dates/counts; merges duplicate matches | `Load()`, `ParseDate()` |
| internal/soccer/store.go | Core data model (Match, Player, Team, Store); dedup + cup-stage inference | `Store`, `Match`, `Player`, `Team`, `Dataset` |
| internal/soccer/matches.go | Match search, last meeting, head-to-head, derbies | `SearchMatches()`, `LastMeeting()`, `HeadToHead()` |
| internal/soccer/teams.go | Team records, rankings, competitions played, club profile, name resolution | `TeamRecord()`, `RankTeams()`, `TeamCompetitions()`, `ClubProfile()`, `ResolveTeam()`, `FindTeams()` |
| internal/soccer/players.go | Player search and profile, Brazilian-players-by-club summary | `SearchPlayers()`, `PlayerProfile()`, `PlayersAtBrazilianClubs()` |
| internal/soccer/competitions.go | Competition identity, standings, knockout brackets | `ResolveCompetition()`, `Standings()`, `Bracket()`, competition constants |
| internal/soccer/statistics.go | Aggregate stats, biggest wins, season comparison, dataset overview | `CompetitionStats()`, `BiggestWins()`, `CompareSeasons()`, `Overview()` |
| internal/soccer/names.go | Team-name normalization (accents, state suffixes, aliases) | `NormalizeTeam()` |
| internal/soccer/names_test.go | Unit tests for name normalization | 2 test functions |
| internal/soccer/store.go tests | — | (none; store tested via acceptance) |
| internal/mcpserver/server_test.go | Unit tests for the JSON-RPC server | 1 test function |
| acceptance/main_test.go | Builds the server binary once for all specs | `TestMain` |
| acceptance/*_test.go | Executable specifications in domain language (match/team/player/competition/statistics/provided-data/assistant) | 45+ `Should…` specs |
| acceptance/dsl/*.go | Domain-specific test language, decomposed by area | `New()`, `NewWithProvidedData()`, area helpers |
| acceptance/driver/*.go | Protocol driver reaching the server as a subprocess over MCP | `SoccerDriver` interface, `NewSyntheticDriver()`, MCP client |

Build artifacts and the `data/` CSV payload are excluded.
