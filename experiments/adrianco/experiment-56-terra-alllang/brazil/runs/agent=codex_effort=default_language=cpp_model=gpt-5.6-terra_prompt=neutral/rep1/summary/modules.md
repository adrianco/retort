# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| soccer.hpp | Core data model + Database API declarations | `soccer::Match`, `Player`, `Record`, `Database`, `normalize`, `match_text`, `record_text` |
| soccer.cpp | CSV loading, team-name normalization, query/aggregation logic | `Database::load`, `find_matches`, `find_players`, `team_record`, `standings`, `answer` |
| main.cpp | MCP JSON-RPC stdio server: dispatch, tool schemas, arg parsing | `main`, `tools_list`, `call`, `result` |
| tests.cpp | BDD-style integration test harness (loads real CSVs) | `main` (5 assertion scenarios) |
| CMakeLists.txt | Build: `soccer_core` lib, `brazilian-soccer-mcp` exe, `soccer_tests` + CTest | `soccer_core`, `brazilian-soccer-mcp`, `soccer_tests` |
