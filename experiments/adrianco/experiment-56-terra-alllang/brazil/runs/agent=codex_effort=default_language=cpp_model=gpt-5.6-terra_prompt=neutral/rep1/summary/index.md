# Summary: cpp · codex · gpt-5.6-terra · neutral · rep 1

- **Shape:** C++17 MCP stdio server (JSON-RPC) over in-memory CSV datasets; CMake build with CTest.
- **Structure:** 3 source modules (soccer.hpp/soccer.cpp/main.cpp) + 1 test file + CMakeLists; ~173 LOC total.
- **Interfaces:** 6 MCP tools (search_matches, team_statistics, head_to_head, standings, search_players, ask_brazilian_soccer); 5 Database API methods; loads all 6 CSVs.
- **Notable:** Extremely compact (dense one-line functions); hand-rolled JSON + UTF-8 accent folding with no external deps. One correctness defect: overlapping Brasileirão seasons (2012–2019) are double-counted in standings/records.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
