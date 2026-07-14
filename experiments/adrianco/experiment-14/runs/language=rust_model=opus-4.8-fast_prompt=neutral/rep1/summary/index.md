# Summary: language=rust model=opus-4.8-fast prompt=neutral · rep 1

- **Shape:** Rust MCP server (JSON-RPC 2.0 over stdio) with an in-memory CSV-backed query engine over Brazilian soccer datasets.
- **Structure:** 7 source modules (lib/main/model/normalize/loader/db/mcp) + 1 integration test file; 28 `#[test]` functions total (22 integration, 10 inline unit). 3 runtime deps (serde, serde_json, csv) — no MCP SDK crate; the protocol is hand-rolled.
- **Interfaces:** 9 MCP tools (find_matches, head_to_head, team_record, standings, search_players, league_stats, biggest_wins, team_competitions, list_competitions); 4 JSON-RPC methods; CLI with `--selftest`.
- **Notable:** Strong team-name normalization (accents, state suffixes, ambiguous-club disambiguation, cross-dataset aliases) and cross-file fixture de-duplication. Standings/records/stats all computed on demand from match edges, not hardcoded. Hand-rolled MCP (no SDK) keeps the dependency footprint tiny.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
