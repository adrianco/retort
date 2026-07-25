# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.m | Executable entry point; arg parsing, chooses stdio-serve / `--list-tools` / `--call` modes | `main()`, `BSDefaultDataDirectory()` |
| src/BSMCPServer.h/.m | JSON-RPC 2.0 / MCP dispatch over stdio; handles initialize, ping, tools/list, tools/call | `BSMCPServer`, `-handleMessage:`, `-handleLine:`, `-runOnStandardIO`, `BSMCPSupportedProtocolVersions()` |
| src/BSTools.h/.m | The 17-tool MCP surface (match/team/player/competition/stats queries) plus text renderers | `BSTools`, `BSToolResult`, `-toolDefinitions`, `-callTool:arguments:`, `-hasToolNamed:` |
| src/BSToolSupport.h/.m | Shared tool plumbing: LLM-loose argument coercion, JSON-Schema builders, answer-text renderers | `BSArgString/Integer/Bool/Limit/Date()`, `BSSchema*()` |
| src/BSKnowledgeGraph.h/.m | In-memory graph of clubs/matches/players; loads once then reconciles duplicate fixtures across files | `BSKnowledgeGraph`, `BSGraphStats`, `+graphWithDataDirectory:error:`, `-mergeStagedMatches:` |
| src/BSDataLoader.h/.m | Per-file CSV adapters that stage BSMatch/BSPlayer objects (no dedup) | `BSDataLoader`, `BSLoadResult`, `-initWithDirectory:registry:` |
| src/BSCSVParser.h/.m | Streaming RFC-4180 CSV reader (BOM, embedded commas, CRLF, ragged rows) | `BSCSVParser`, `BSCSVRow`, `-stringForColumn:` |
| src/BSClubRegistry.h/.m | Canonicalizes ~700 raw team strings into ~90 real club nodes via fold/peel/lookup pipeline | `BSClubRegistry`, `BSNameParts`, resolve APIs |
| src/BSClub.h/.m | Club node model | `BSClub` |
| src/BSMatch.h/.m | Match/fixture node model | `BSMatch` |
| src/BSPlayer.h/.m | FIFA player node model | `BSPlayer` |
| src/BSQuery.h/.m | Declarative match filter + engine that picks the cheapest starting index | `BSMatchFilter`, query engine, `BSVenue`, `BSVenueFromString()` |
| src/BSAnalytics.h/.m | Computed results: W/D/L records, league tables (CBF tie-breaks), head-to-head, aggregates | `BSTeamRecord`, `BSStandings`, analytics functions |
| src/BSCommon.h/.m | Shared vocabulary: competition ids, source-file ids, competition normalization | `BSCompetition*` constants, `BSCompetitionNormalize()` |
| src/BSDateUtil.h/.m | Multi-format date parsing (ISO, dd/mm/yyyy, with-time) | `BSDate`, `BSArgDate` helpers |
| src/BSTextUtil.h/.m | String folding / accent-insensitive text utilities | text normalization helpers |
| tests/BSTest.h/.m | BDD test harness (`BSFeature/BSScenario/BSGiven/BSWhen/BSThen*`); shared graph loaded once | `BSTest`, scenario macros |
| tests/test_main.m | Test runner entry point | `main()` |
| tests/BSTestParsing.m | ~14 scenarios for CSV, date, and text parsing primitives | scenario functions |
| tests/BSTestGraph.m | ~15 scenarios for loading and cross-source fixture reconciliation | scenario functions |
| tests/BSTestQueries.m | ~22 scenarios: the spec's Gherkin queries plus numeric anchor checks | scenario functions |
| tests/BSTestMCP.m | ~19 protocol-level scenarios driven through `-handleLine:` (real JSON framing) | scenario functions |
| tests/BSTestNormalization.m | ~9 club-registry regression scenarios (Atlético-MG vs Athletico-PR etc.) | scenario functions |
| tests/BSTestSampleQuestions.m | ~29 scenarios working through the spec's sample questions (≥20 bar) | scenario functions |
