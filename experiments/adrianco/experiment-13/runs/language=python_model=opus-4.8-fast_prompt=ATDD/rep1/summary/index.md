# Summary: language=python_model=opus-4.8-fast_prompt=ATDD · rep 1

- **Shape:** Python MCP server (FastMCP) over an in-memory CSV-backed knowledge base for Brazilian soccer.
- **Structure:** 6 source modules, 3 test files (acceptance / unit / real-data) + conftest.
- **Interfaces:** 6 MCP tools (find_matches, get_team_record, head_to_head, search_players, get_standings, get_competition_stats); 1 console script; 0 HTTP routes.
- **Notable:** ATDD prompt followed — black-box acceptance suite drives the system only through a real in-memory MCP client/server session, each scenario seeding its own temp dataset; thoughtful team-name normalization and multi-source dedup (one primary source per competition-season).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
