# Summary: effort=low language=swift model=claude-opus-5-5 prompt=neutral · rep 1

- **Shape:** Swift Package MCP server (stdio JSON-RPC 2.0) over an in-memory store built from six Brazilian-soccer Kaggle CSVs, with a hand-rolled CSV parser and no external dependencies.
- **Structure:** 9 source files (1 executable + 8 library) across a `BrazilianSoccer` library and a `brazilian-soccer-mcp` executable; 4 test files (3 with tests), 31 test functions total.
- **Interfaces:** 15 MCP tools (matches, teams, standings, brackets, stats, rankings, derbies, players, dataset summary), 0 HTTP routes, 1 CLI entry (`--data-dir`), 6 handled JSON-RPC methods.
- **Notable:** Heavy investment in team-name normalisation (accent folding, alias/affix stripping, per-state disambiguation via `TeamResolver`) and cross-file fixture de-duplication (merge within 2 days); no database or async — everything is eager in-memory scans. Comments document dataset quirks (2020 season split into 2021, bad UF columns, FIFA dataset missing major clubs).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
