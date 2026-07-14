# Summary: language=go · model=opus-4.8-fast · prompt=TDD · rep 2

- **Shape:** Go stdlib-only MCP server (JSON-RPC 2.0 over stdio) over an in-memory knowledge base of Brazilian soccer CSVs.
- **Structure:** 12 implementation modules (~1,594 LOC) across `internal/mcp` (protocol/tools) and `internal/soccer` (data + query engine); 13 test files (~1,008 LOC, 50 test functions); zero external dependencies.
- **Interfaces:** 6 MCP tools (search_matches, head_to_head, team_record, search_players, standings, competition_stats) + 5 protocol methods; 1 CLI flag (`-data`).
- **Notable:** Clean layering with explicit cross-dataset deduplication (`pickSource`/`DedupedMatches`) to avoid double-counting overlapping sources; accent/suffix-insensitive team matching; integration tests assert against real data (2019 Brasileirão champion = Flamengo, 90 pts; 827 Brazilian FIFA players; 18,207 players total).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
