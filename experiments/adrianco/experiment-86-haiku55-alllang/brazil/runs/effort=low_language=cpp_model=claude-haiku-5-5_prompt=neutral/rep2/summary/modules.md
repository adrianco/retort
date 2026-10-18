# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.cpp | Executable entry: parses `--data-dir`, loads the store, serves MCP over stdin/stdout | `main()` |
| src/mcp_server.h / .cpp | JSON-RPC 2.0 / MCP server over newline-delimited stdio | `McpServer`, `ToolDef`, `handle()`, `run()` |
| src/tools.h / .cpp | The 9 MCP tool definitions and their argument parsing / text formatting | `make_tools()` |
| src/queries.h / .cpp | Query layer over DataStore: match search, records, standings, stats, player search | `find_matches()`, `record_for()`, `standings()`, `league_stats()`, `biggest_wins()`, `search_teams()`, `search_players()`, `club_summary()`, structs `MatchQuery`, `Record`, `StandingRow`, `LeagueStats`, `PlayerQuery`, `ClubSummary` |
| src/data_store.h / .cpp | In-memory store loading the 6 Kaggle CSVs into matches + players, with dedup/overlap handling | `DataStore`, `Match`, `Player`, `LoadReport`, `load_data_store()`, `canonical_competition()` |
| src/team.h / .cpp | Team-name normalization (strips state suffix, folds full names to one key) | `TeamName`, `parse_team_name()`, `same_team()` |
| src/text.h / .cpp | Text helpers: trim, case, accent folding, date and number parsing | `trim()`, `lower_ascii()`, `upper_ascii()`, accent fold, `parse_date()` |
| src/csv.h / .cpp | RFC 4180-style CSV reader (quoted fields, doubled quotes, CRLF, BOM) | `CsvTable`, CSV read helpers |
| src/json.h / .cpp | Minimal JSON value, parser and serializer for the JSON-RPC layer | `json::Value`, `parse()`, `dump()` |
| tests/test_main.cpp | Test runner: iterates the registry, prints pass/fail | `main()` |
| tests/test_core.cpp | Unit scenarios for JSON, CSV, text folding, dates, team names | 12 `TEST(...)` cases |
| tests/test_data.cpp | Scenarios against the real Kaggle files in `DATA_DIR`: loading + queries | 14 `TEST(...)` cases |
| tests/test_server.cpp | MCP protocol scenarios: handshake, tool listing, calls, errors, notifications | 9 `TEST(...)` cases |
| tests/test_framework.h | Minimal test registry + assertion macros | `TEST`, `test_registry()` |
| tests/test_support.h | Shared test fixtures/helpers | fixture helpers |
| CMakeLists.txt | Build: `soccer_core` static lib, `brazilian_soccer_mcp` exe, `soccer_tests` | targets |
