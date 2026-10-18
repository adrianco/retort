# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.m | Wires dataset → engine → server, runs stdio loop | `main()` |
| src/CSVParser.h/.m | CSV reader (quoting, embedded newlines, BOM/CRLF) | `+parseRows:`, `+parseRecords:` |
| src/SoccerText.h/.m | Name/date/competition normalisation primitives | `+keyForTeam:`, `+displayNameForTeam:`, `+isoDateFromString:`, `+competitionForQuery:`, `+canonicalCompetition:`, `+integerFromString:` |
| src/SoccerDataset.h/.m | Loads 6 CSVs into records, de-dups, indexes | `SoccerMatch`, `SoccerPlayer`, `SoccerDataset` (`-loadDirectory:error:`, `-importCSVText:fileName:`, `-resolveTeam:`, `-matchesForTeamKey:`, `-brazilianClubNameForClub:`) |
| src/QueryEngine.h/.m | Structured soccer queries → plain-text answers | `MatchFilter`, `QueryEngine` (`-searchMatches:limit:error:`, `-teamRecord:error:`, `-headToHead:error:`, `-standingsForCompetition:season:error:`, `-leagueStats:error:`, `-biggestWins:limit:error:`, `-searchPlayersNamed:...`, `-brazilianClubSummary`) |
| src/MCPServer.h/.m | JSON-RPC 2.0 dispatch, tool schemas, stdio transport | `MCPServer` (`-handleMessage:`, `-handleLine:`, `-runWithInput:output:`, `+toolDefinitions`) |
| tests/test_main.m | BDD-style harness, 40 scenarios / 153 checks | `main()`, `kScenarios[]` |
| Makefile | Build + test (Foundation only, ARC) | `all`, `test`, `clean` |
