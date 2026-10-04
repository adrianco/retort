# Summary: effort=low language=elixir model=claude-opus-5-5 prompt=neutral · rep 1

- **Shape:** Elixir MCP server (JSON-RPC 2.0 over stdio) over six in-memory Kaggle CSVs of Brazilian soccer, zero external deps (stdlib only, including the built-in `JSON` and a hand-written CSV parser).
- **Structure:** 12 source modules (~1,325 LOC in lib) + 1 Mix task + config; 3 test files with 67 test functions.
- **Interfaces:** 4 MCP JSON-RPC methods, 14 MCP tools, 1 CLI/Mix task, ~30 exported query/store/text functions; data merged into 5 competitions plus the FIFA player DB.
- **Notable:** Unusually thorough for a low-effort run — a full RFC 4180 CSV parser, cross-file fixture de-duplication (dates within 2 days), extensive team-name normalisation (state disambiguation, aliases, affix stripping), 25 named derby rivalries, and standings with champion/relegation logic. Data held in `:persistent_term`; all queries are pure in-memory linear scans; tool output is plain text, not structured JSON.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
