# Summary: language=rust · model=opus-4.8-fast · prompt=ATDD · rep 1

- **Shape:** Rust MCP server (JSON-RPC 2.0 over stdio) over Brazilian soccer CSVs; std + serde/serde_json/csv only.
- **Structure:** 7 source modules, 2 test files (17 acceptance tests + 6 inline unit tests).
- **Interfaces:** 7 MCP tools (match/team/head-to-head/player/standings/stats/competitions); no HTTP, no external APIs.
- **Notable:** Genuine black-box acceptance suite spawning the compiled binary and speaking MCP — strong ATDD adherence; curated team-alias table that avoids the same-name-merge trap; de-dup unifies overlapping source files.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
