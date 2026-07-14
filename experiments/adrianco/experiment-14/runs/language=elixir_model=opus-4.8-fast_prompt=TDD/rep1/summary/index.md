# Summary: language=elixir model=opus-4.8-fast prompt=TDD · rep 1

- **Shape:** Elixir MCP server (JSON-RPC 2.0 over stdio escript) over an in-memory dataset loaded from Kaggle CSVs — no external deps, no database.
- **Structure:** 17 lib modules, 15 test files (91 tests, 36 describe blocks, 0 skips).
- **Interfaces:** 10 MCP tools / 1 escript CLI / no HTTP routes.
- **Notable:** Clean layering (CSV → DataLoader → Dataset → Queries.* → MCP.{Tools,Server,CLI}); pure `Server.handle/2` with transport isolated for testability; a dedicated `Source.primary_per_season/1` resolves the same fixture appearing across multiple overlapping CSVs so standings/records/stats aren't double-counted. Standard-library only (`deps: []`, uses built-in `JSON`).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
