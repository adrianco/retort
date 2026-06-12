# Summary: language=python_model=opus-4.8-fast_prompt=ATDD · rep 3

- **Shape:** Python MCP server (FastMCP over stdio) over pandas tables loaded from the bundled Kaggle CSVs; clean 3-layer split (server → service → repository) plus a name-normalization module.
- **Structure:** 5 source modules + 2 test files (1 acceptance, 1 unit); 31 test functions total.
- **Interfaces:** 8 MCP tools (matches, team record, head-to-head, player search, standings, competition stats, team competitions, cross-file team profile); 1 CLI demo; no HTTP routes.
- **Notable:** Acceptance tests drive the server through the *real* MCP protocol (`create_connected_server_and_client_session` + `ClientSession`), exactly the ATDD "public interface only" mandate. De-duplicates three overlapping Brasileirão sources so 2019 Serie A resolves to exactly 380 matches. Row-wise `iterrows()` aggregation is the main non-idiomatic spot.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
