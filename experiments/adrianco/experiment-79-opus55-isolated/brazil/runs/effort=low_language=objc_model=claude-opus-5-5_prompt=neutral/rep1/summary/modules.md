# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.m | CLI entry: locates data dir, loads store, serves MCP over stdio or runs one tool | `main()`, `FindDataDirectory()` |
| src/BSMCPServer.h/.m | JSON-RPC 2.0 MCP server over stdin/stdout (initialize, tools/list, tools/call, ping, batch) | `BSMCPServer`, `-run`, `-handleLine:`, `-handleMessage:` |
| src/BSTools.h/.m | Tool catalogue (17 tools) + argument parsing, dispatch and text formatting | `BSTools`, `-toolDefinitions`, `-callTool:arguments:error:` |
| src/BSQueryEngine.h/.m | Query/aggregation over matches and players: filter, records, standings, rankings, aggregates | `BSQueryEngine`, `BSMatchFilter`, `BSRecord`, `BSAggregate`, `-findMatches:`, `-standingsForCompetition:season:` |
| src/BSDataStore.h/.m | Loads/merges the six Kaggle CSVs into matches + FIFA players; team-name resolution | `BSDataStore`, `-loadFromDirectory:error:`, `-resolveTeam:`, `BSMatch`, `BSPlayer` |
| src/BSTeamNames.h/.m | Team-name normalisation, competition canonicalisation, date parsing, derby detection | `BSTeamNames`, `+keyForName:`, `+fold:`, `+derbyNameForKey:andKey:`, `BSCanonicalCompetition()`, `BSNormalizeDate()` |
| src/BSCSV.h/.m | RFC-4180-ish CSV parser (quotes, embedded commas, CRLF, BOM) | `BSCSV`, `+rowsFromData:` |
| tests/BSTests.m | BDD-style test suite over the real CSVs + in-process and end-to-end MCP checks | `main()`, 10 feature functions |

All source is Objective-C (Foundation only, ARC). No build artifacts present in the archive.
