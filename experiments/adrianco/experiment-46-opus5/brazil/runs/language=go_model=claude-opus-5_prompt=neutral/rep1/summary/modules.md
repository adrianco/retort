# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry point; parses flags, loads datasets, serves MCP over stdio or runs CLI tool/list/check paths | `main()`, `run()`, `isCleanShutdown()`, `connect()`, `listTools()`, `callTool()`, `printCheck()` |
| main_test.go | BDD-style tests for the CLI paths (`-check`, `-list-tools`, `-tool`, clean shutdown) | ~7 scenario tests |
| internal/mcpserver/server.go | MCP server over the go-sdk; registers 18 tools + 2 resources and their handlers, arg structs and result shaping | `New()`, `Server`, `(*Server).MCP()`, `(*Server).Run()`, `Version`, `Instructions` |
| internal/mcpserver/server_test.go | In-memory MCP client tests exercising every tool via round trips | ~20 scenario tests |
| internal/soccer/model.go | Core domain types: Club, Match, Player, ExtendedStats, Competition; describe/score helpers | `Club`, `Match`, `Player`, `Competition`, `AllCompetitions`, `DatasetInfo`, `(*Match).Outcome/ScoreLine/Describe` |
| internal/soccer/graph.go | Knowledge graph build: loads six CSVs, dedups fixtures, builds indexes; accessors | `Graph`, `Load()`, `LoadFS()`, `FindDataDir()`, `Summary()`, `Stats`, `ParseCompetition()`, club/match/player accessors |
| internal/soccer/loader.go | CSV table reader and per-file row parsers; date/int parsing; player and extended-stats loading | `readTable()`, `parseDate()`, `PositionGroup()`, `loadBrasileirao/Historical/Cup/Libertadores/BRFootball/Players` |
| internal/soccer/normalize.go | Team-name normalization: accents, state suffixes, club-type tokens, name parts/keys | `NameParts`, `ParseTeamName()`, `RegionName()`, `IsBrazilianState()`, `normalizeText()`, `containsNormalized()` |
| internal/soccer/resolver.go | Resolves raw team-name strings to stable club IDs using curated + observed names | `resolver`, `newResolver()`, `resolve()`, `slugify()` |
| internal/soccer/clubs.go | Curated data tables: known clubs, FIFA-club→club-ID map, classic rivalries | `knownClubs`, `fifaClubToClubID`, `classicRivalries` |
| internal/soccer/query.go | Club resolution and match filtering (team, opponent, venue, competition, season, date range, stage) | `ResolveClub()`, `MustResolveClub()`, `SearchClubs()`, `MatchFilter`, `FindMatches()`, `ParseVenue()`, `ParseDateArg()` |
| internal/soccer/stats.go | Aggregations: records, team stats, head-to-head, standings, competition aggregates, leaderboards, season comparison, derbies | `TeamStats()`, `HeadToHead()`, `Standings()`, `Champion()`, `AggregateStats()`, `Leaderboard()`, `CompareSeasons()`, `Derbies()`, `BuildRecord()`, `RivalryName()` |
| internal/soccer/players.go | FIFA player search, sorting and summarization by club/nationality | `PlayerFilter`, `SearchPlayers()`, `FindPlayer()`, `PlayerByID()`, `SummarizeByClub()`, `SummarizeByNationality()`, `TopSkills()` |
| internal/soccer/format.go | Human-readable formatting of matches, records, standings, leaderboards, players | `FormatMatchList()`, `FormatTeamStats()`, `FormatHeadToHead()`, `FormatStandings()`, `FormatLeaderboard()`, `FormatPlayerProfile()`, `FormatMatchDetail()` |
| internal/soccer/graph_test.go | Tests for graph load, dedup, indexes, accessors | scenario tests |
| internal/soccer/query_test.go | Tests for club resolution and match filtering | scenario tests |
| internal/soccer/normalize_test.go | Tests for team-name normalization | scenario tests |
| internal/bdd/bdd.go | Tiny Given/When/Then harness (`S`, `Feature`, step logging) used by the test suite | `S`, `Feature`, `Scenario`, step helpers |

Notes:
- 12 non-test source files plus 5 test files (one is the shared `bdd` harness, itself non-test code used only by tests).
- `cmd/` and `data/kaggle/` hold no Go source (data CSVs only).
