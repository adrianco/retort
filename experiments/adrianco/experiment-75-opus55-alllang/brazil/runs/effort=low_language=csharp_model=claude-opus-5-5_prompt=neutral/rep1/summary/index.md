# Summary: effort=low_language=csharp_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** C# / .NET 10 MCP server (hand-rolled JSON-RPC over stdio) with an in-memory LINQ query layer over six Kaggle CSVs.
- **Structure:** 6 source modules, 3 test files (+ shared fixture); 15 MCP tools.
- **Interfaces:** 4 JSON-RPC methods, 15 MCP tools, 1 CLI mode; no HTTP.
- **Notable:** Careful cross-dataset handling — team-name normalization with alias regexes, match deduplication across overlapping files, and single-source-per-season standings to avoid double-counting. Well beyond the minimum spec (derbies, compare_seasons, best_records, biggest_wins).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
