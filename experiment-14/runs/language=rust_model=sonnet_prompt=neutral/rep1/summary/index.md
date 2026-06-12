# Summary: language=rust_model=sonnet_prompt=neutral · rep 1

- **Shape:** Rust stdio MCP server (hand-rolled JSON-RPC) over an in-memory CSV-backed soccer dataset.
- **Structure:** 4 source modules, tests inline (15 `#[test]` across data.rs + tools.rs).
- **Interfaces:** 5 JSON-RPC methods, 8 MCP tools, 2 in-memory data models (Match, Player).
- **Notable:** No MCP SDK dependency — only serde/serde_json/csv/anyhow. All queries are linear scans; date-range filter and default-scope team aggregation have data-quality edges (see flow.md).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
