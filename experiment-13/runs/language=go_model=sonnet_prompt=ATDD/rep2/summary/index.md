# Summary: language=go_model=sonnet_prompt=ATDD · rep 2

- **Shape:** Go MCP server (JSON-RPC over stdio), pure stdlib, in-memory dataset loaded from Kaggle CSVs
- **Structure:** 4 source modules + 1 acceptance test file (15 black-box tests)
- **Interfaces:** 5 MCP tools (find_matches, get_team_stats, find_players, get_standings, get_statistics); no external deps
- **Notable:** ATDD-style suite drives the system only through the public `Call` interface; clean loader/query/server layering; team matching uses lenient bidirectional substring containment

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
