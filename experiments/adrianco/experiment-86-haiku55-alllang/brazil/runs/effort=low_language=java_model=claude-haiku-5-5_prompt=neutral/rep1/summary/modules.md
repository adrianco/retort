# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/br/soccer/Main.java | Entry point: loads data dir, wires server to stdio | `main()` |
| src/main/java/br/soccer/mcp/McpServer.java | JSON-RPC 2.0 MCP server over newline-delimited stdio | `serve()`, `handle()` |
| src/main/java/br/soccer/mcp/SoccerTools.java | MCP tool catalogue (7 tools) + argument parsing | `definitions()`, `has()`, `call()` |
| src/main/java/br/soccer/data/DataLoader.java | Reads the six Kaggle CSVs into a `Dataset`, dedups, labels cup finals | `load()` |
| src/main/java/br/soccer/data/Dataset.java | In-memory read-only query surface over matches/players | `findMatches()`, `teamRecord()`, `headToHead()`, `standings()`, `findPlayers()`, `clubSummary()`, `biggestWins()`, `venueRecords()`, `outcomeRates()`, `goalsPerMatch()` |
| src/main/java/br/soccer/data/Match.java | Match record + per-team goal/venue helpers | `Match`, `of()`, `isHome()`, `involves()`, `margin()` |
| src/main/java/br/soccer/data/Player.java | FIFA player record | `Player` |
| src/main/java/br/soccer/data/MatchFilter.java | Match query criteria + `Venue` enum | `MatchFilter`, `Venue` |
| src/main/java/br/soccer/data/PlayerFilter.java | Player query criteria + predicate | `PlayerFilter`, `test()` |
| src/main/java/br/soccer/data/TeamNames.java | Team-name normalization (state suffixes, aliases, accents) | `key()`, `display()` |
| src/main/java/br/soccer/data/Text.java | Accent folding, whitespace, int/date parsing (multi-format) | `fold()`, `compact()`, `parseInt()`, `parseDate()` |
| src/main/java/br/soccer/data/Csv.java | Minimal RFC-4180-ish CSV reader with header map | `readTable()`, `parse()`, `Table` |
| src/test/java/br/soccer/data/SoccerDataBddTest.java | Given/When/Then scenarios over real data | 24 tests |
| src/test/java/br/soccer/mcp/McpServerTest.java | JSON-RPC protocol tests | 10 tests |
| src/test/java/br/soccer/mcp/SoccerToolsTest.java | Tool catalogue + call tests | 8 tests |
| src/test/java/br/soccer/data/TeamNamesTest.java | Name-normalization tests | 7 tests |
| src/test/java/br/soccer/data/CsvTest.java | CSV parser tests | 4 tests |
| src/test/java/br/soccer/data/TextTest.java | Text/date parsing tests | 3 tests |
