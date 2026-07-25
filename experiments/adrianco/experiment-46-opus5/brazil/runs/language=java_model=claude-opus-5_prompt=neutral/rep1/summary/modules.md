# Modules

Java 21 Maven project (`com.brazilsoccer.mcp`). 30 main source files + 7 test files + 7 Cucumber feature files. Built as a shaded jar exposing an MCP server over stdio.

## Main sources

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/com/brazilsoccer/mcp/BrazilianSoccerMcpServer.java | CLI entry point; parses args, loads data, runs MCP over stdio or one-shot `--call`/`--list-tools` | `main()` |
| src/main/java/com/brazilsoccer/mcp/McpServerFactory.java | Adapts transport-independent tools to the MCP Java SDK; builds stdio server | `createStdio()`, `create()`, `toolSpecifications()`, `INSTRUCTIONS` |
| src/main/java/com/brazilsoccer/mcp/data/DataLoader.java | Reads the six Kaggle CSVs, merges overlapping fixtures, builds the graph | `load()`, `resolveDefaultDirectory()`, `DEFAULT_DATA_DIR` |
| src/main/java/com/brazilsoccer/mcp/graph/KnowledgeGraph.java | In-memory graph with adjacency indexes over teams/matches/players/competitions | `KnowledgeGraph`, `DatasetInfo`, `LoadReport`, `registry()` |
| src/main/java/com/brazilsoccer/mcp/graph/TeamRegistry.java | Canonicalises club spellings; fuzzy search for teams | `TeamRegistry`, `search()`, `register()` |
| src/main/java/com/brazilsoccer/mcp/graph/TeamNameNormalizer.java | Normalises club name spellings/accents/state suffixes | `TeamNameNormalizer` |
| src/main/java/com/brazilsoccer/mcp/model/Match.java | Match node record (teams, score, season, competition, stats, sources) | `Match` (record) |
| src/main/java/com/brazilsoccer/mcp/model/MatchStats.java | Optional extended stats (corners, shots, attacks) | `MatchStats` (record), `hasAnyValue()` |
| src/main/java/com/brazilsoccer/mcp/model/Player.java | FIFA player node record (ratings, club, position) | `Player` (record) |
| src/main/java/com/brazilsoccer/mcp/model/Team.java | Club node with id, display name, state, counts | `Team`, `qualifiedName()` |
| src/main/java/com/brazilsoccer/mcp/model/Competition.java | Enum of the 5 competitions with ids and lenient parse | `Competition`, `parse()`, `id()`, `isLeague()` |
| src/main/java/com/brazilsoccer/mcp/query/MatchQuery.java | Mutable filter builder (team/competition/season/date/venue/round/limit) | `MatchQuery`, `create()` |
| src/main/java/com/brazilsoccer/mcp/query/MatchQueryService.java | Runs match filters against the graph indexes; head-to-head | `findAll()`, `find()`, `headToHead()`, `HeadToHead` |
| src/main/java/com/brazilsoccer/mcp/query/TeamStatsService.java | Aggregates a club's W/D/L, goals, per-competition records | `TeamStatsService` |
| src/main/java/com/brazilsoccer/mcp/query/TeamRecord.java | W/D/L + goals tally record with derived rates | `TeamRecord` (record) |
| src/main/java/com/brazilsoccer/mcp/query/CompetitionService.java | Computes season standings tables and summaries from match results | `CompetitionService` |
| src/main/java/com/brazilsoccer/mcp/query/PlayerQueryService.java | Searches/filters FIFA players by name/nationality/club | `PlayerQueryService` |
| src/main/java/com/brazilsoccer/mcp/query/StatisticsService.java | Aggregate metrics: goals/match, home advantage, biggest wins, rankings | `StatisticsService` |
| src/main/java/com/brazilsoccer/mcp/query/Rivalries.java | Known classic derbies (Fla-Flu, etc.) lookup | `Rivalries` |
| src/main/java/com/brazilsoccer/mcp/query/Venue.java | HOME/AWAY/ALL venue filter enum with parse | `Venue`, `parse()` |
| src/main/java/com/brazilsoccer/mcp/format/Formatters.java | Renders matches/tables/players as human-readable text answers | `Formatters`, `matchList()` |
| src/main/java/com/brazilsoccer/mcp/tools/SoccerTool.java | Transport-independent tool record (name/schema/handler) | `SoccerTool` (record), `call()` |
| src/main/java/com/brazilsoccer/mcp/tools/ToolRegistry.java | Assembles + dispatches the 15-tool catalogue | `ToolRegistry`, `tools()`, `call()` |
| src/main/java/com/brazilsoccer/mcp/tools/ToolContext.java | Shared services + argument resolution (team/competition/filters) | `ToolContext`, `requireTeam()`, `baseQuery()` |
| src/main/java/com/brazilsoccer/mcp/tools/ToolArguments.java | Typed accessors over the raw MCP argument map | `ToolArguments`, `of()`, `string()`, `integer()`, `date()` |
| src/main/java/com/brazilsoccer/mcp/tools/Schemas.java | Fluent JSON-schema builder for tool input schemas | `Schemas`, `object()` |
| src/main/java/com/brazilsoccer/mcp/tools/ToolException.java | Caller-visible error (unknown club, bad arg) | `ToolException` |
| src/main/java/com/brazilsoccer/mcp/tools/GraphTools.java | `dataset_info` tool | `create()` |
| src/main/java/com/brazilsoccer/mcp/tools/MatchTools.java | `search_matches`, `head_to_head`, `find_derbies` tools | `create()` |
| src/main/java/com/brazilsoccer/mcp/tools/TeamTools.java | `team_stats`, `team_competitions`, `list_teams` tools | `create()` |
| src/main/java/com/brazilsoccer/mcp/tools/CompetitionTools.java | `standings`, `competition_summary`, `compare_seasons` tools | `create()` |
| src/main/java/com/brazilsoccer/mcp/tools/PlayerTools.java | `search_players`, `player_profile`, `player_club_summary`, `player_club_report` tools | `create()` |
| src/main/java/com/brazilsoccer/mcp/tools/StatsTools.java | `statistics` tool (overview/biggest_wins/highest_scoring/team_ranking) | `create()` |
| src/main/java/com/brazilsoccer/mcp/util/CsvReader.java | Streaming CSV parser (quotes, headers) | `CsvReader` |
| src/main/java/com/brazilsoccer/mcp/util/DateParsers.java | Parses the several date formats across datasets | `DateParsers` |
| src/main/java/com/brazilsoccer/mcp/util/TextUtils.java | Accent stripping / slug / normalisation helpers | `TextUtils` |

## Tests

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/test/java/com/brazilsoccer/mcp/McpProtocolTest.java | MCP protocol / tool-call integration tests | 6 @Test |
| src/test/java/com/brazilsoccer/mcp/graph/KnowledgeGraphTest.java | Graph loading, indexing, merge behaviour | 10 @Test |
| src/test/java/com/brazilsoccer/mcp/graph/TeamNameNormalizerTest.java | Club name normalisation cases | 5 @Test |
| src/test/java/com/brazilsoccer/mcp/tools/ToolCatalogTest.java | Tool catalogue / schema validity | 6 @Test |
| src/test/java/com/brazilsoccer/mcp/tools/QueryPerformanceTest.java | Query latency guards | 3 @Test |
| src/test/java/com/brazilsoccer/mcp/util/CsvReaderTest.java | CSV parsing edge cases | 5 @Test |
| src/test/java/com/brazilsoccer/mcp/util/DateParsersTest.java | Date parsing formats | 4 @Test |
| src/test/java/com/brazilsoccer/mcp/support/TestFixtures.java | Shared in-memory graph fixtures | helper (no @Test) |
| src/test/java/com/brazilsoccer/mcp/bdd/RunCucumberTest.java | JUnit Platform runner for Cucumber features | runner |
| src/test/java/com/brazilsoccer/mcp/bdd/SoccerStepDefinitions.java | Step definitions for the 7 feature files | step defs |
| src/test/resources/features/*.feature | 7 Gherkin feature files (48 scenarios total) | — |
