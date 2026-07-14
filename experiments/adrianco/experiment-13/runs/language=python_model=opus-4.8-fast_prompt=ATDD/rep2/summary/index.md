# Summary: language=python_model=opus-4.8-fast_prompt=ATDD · rep 2

- **Shape:** Python MCP server (FastMCP / stdio) over the provided Brazilian-soccer CSV datasets, with a CSV loader → in-memory domain models → query repository layering.
- **Structure:** 5 source modules, 9 test files (7 acceptance + 2 unit), 50 test functions.
- **Interfaces:** 10 MCP tools (find_matches, head_to_head, team_record, competition_standings, competition_winner, list_competitions, competition_statistics, biggest_wins, search_players, top_players). No HTTP/CLI surface beyond the `brazilian-soccer-mcp` stdio entry point.
- **Notable:** Textbook ATDD layout — acceptance tests drive the system through the real MCP protocol (`create_connected_server_and_client_session`) with no back-door access; each test seeds its own isolated temp dataset. Repository deliberately separates data loading, normalization (accents/state-suffix/date formats), and query logic.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
