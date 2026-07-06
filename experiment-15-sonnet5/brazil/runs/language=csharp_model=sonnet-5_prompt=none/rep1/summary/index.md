# Summary: language=csharp · model=sonnet-5 · prompt=none · rep 1

- **Shape:** C#/.NET 10 MCP stdio server (official `ModelContextProtocol` SDK) over in-memory CSV data, split into a testable `Data` core + `Server` host.
- **Structure:** 24 source files across 3 projects (Data / Server / Tests), 9 test files.
- **Interfaces:** 13 MCP tools (5 match/team, 4 player, 4 stats); no HTTP/CLI beyond `--data-dir=`.
- **Notable:** Clean layering — all logic lives in the testable `Data` library and the `Server` is a thin MCP adapter; a hand-rolled CSV parser and a careful `TeamNameNormalizer` that unifies name variants while keeping same-name/different-state clubs distinct; standings deliberately computed from a single dataset per call to avoid double-counting overlapping CSVs.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
