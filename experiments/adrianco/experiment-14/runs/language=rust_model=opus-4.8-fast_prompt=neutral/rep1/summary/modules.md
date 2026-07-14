# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Crate root; re-exports the public API | `Database`, `Server` |
| src/main.rs | Binary: loads CSVs, runs JSON-RPC 2.0 stdio loop (MCP transport) | `main()`, `serve_stdio()`, `--selftest` flag |
| src/model.rs | Domain types for the knowledge graph | `Match`, `Player`, `MatchExtras`, `Outcome` |
| src/normalize.rs | Team-name / text normalization (accents, state suffixes, aliases) | `team_key()`, `search_key()`, `display_name()` |
| src/loader.rs | Per-file CSV parsers mapping 6 datasets to the domain model | `load_all()`, `normalize_date()`, `LoadReport` |
| src/db.rs | In-memory query engine over matches + players | `Database`, `MatchFilter`, `PlayerFilter`, `Record`, `HeadToHead`, `LeagueStats`, `StandingRow` |
| src/mcp.rs | MCP JSON-RPC dispatch + 9 tool implementations | `Server`, `tool_definitions()` |
| tests/integration.rs | Full-stack tests over the real datasets | 22 test functions |

Unit tests also live inline in `loader.rs` (3 tests) and `normalize.rs` (7 tests).
Total `#[test]` functions across the crate: 28.
