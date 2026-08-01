# Summary: rust · codex · gpt-5.6-terra · rep 1

- **Shape:** Hand-rolled JSON-RPC (stdio) MCP server in Rust over an in-memory dataset loaded from the provided Kaggle CSVs — no MCP SDK crate, protocol implemented directly.
- **Structure:** 2 source modules (`lib.rs` query engine, `main.rs` server), 3 inline unit tests, no separate test file.
- **Interfaces:** 7 MCP tools (search_matches, team_statistics, head_to_head, search_players, standings, competition_statistics, ask), 0 HTTP routes; ~10 exported library functions.
- **Notable:** Very compact (721 LOC total). Robust team-name normalization (accent stripping + state-suffix + filler-word removal) shared across match and player queries; multi-schema CSV loader tolerant of differing column names (Portuguese and English). All queries are linear scans over in-memory `Vec`s.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
