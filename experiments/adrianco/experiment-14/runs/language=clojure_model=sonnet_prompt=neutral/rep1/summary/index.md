# Summary: language=clojure_model=sonnet_prompt=neutral · rep 1

- **Shape:** Clojure MCP server (JSON-RPC 2.0 over stdio) with in-memory CSV-backed query tools for Brazilian soccer data.
- **Structure:** 4 source modules (core/data/normalize/tools), 1 test file (14 deftests, 50 testing blocks, 89 assertions), 820 source LOC.
- **Interfaces:** 3 MCP protocol methods + 7 query tools; no HTTP/CLI surface. Data loaded from 6 Kaggle CSVs into an atom at startup.
- **Notable:** Goes beyond the spec's 5 capability categories (7 tools incl. biggest-wins and competition-stats); careful team-name normalization with accent/state-code stripping; tools return preformatted text rather than structured JSON.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
