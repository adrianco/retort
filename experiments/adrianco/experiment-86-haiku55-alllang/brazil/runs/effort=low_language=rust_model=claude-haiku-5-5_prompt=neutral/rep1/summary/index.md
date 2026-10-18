# Summary: effort=low language=rust model=claude-haiku-5-5 prompt=neutral · rep 1

- **Shape:** Rust MCP (stdio JSON-RPC 2.0) server over local Kaggle CSVs, with a pure query layer (`csv` + `serde_json`, no async runtime).
- **Structure:** 7 source modules + 2 integration test files + 1 shared fixture (1,855 LOC incl. tests).
- **Interfaces:** 5 MCP methods + 7 MCP tools; library API exports `data`/`normalize`/`query`/`tools`/`mcp`.
- **Notable:** Strong team-name normalization (accent folding, state-suffix handling, long-name aliases, ambiguous-club disambiguation) and dataset dedup across overlapping sources; standings test asserts the real 2019 Brasileirão table (Flamengo 90 pts). Only 2 external crates.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
