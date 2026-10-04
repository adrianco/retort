# Summary: effort=low_language=rust_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Rust MCP server (JSON-RPC 2.0 over stdio) exposing a Brazilian-soccer knowledge base built from six Kaggle CSVs, with a CLI `call`/`tools` mode.
- **Structure:** 6 source modules (~2100 LoC), 1 test file (39 BDD scenarios; 4 more unit tests in normalize.rs → 43 total).
- **Interfaces:** 17 MCP tools + 4 JSON-RPC methods + 3 CLI commands; only `csv` and `serde_json` as dependencies.
- **Notable:** No external MCP SDK — the JSON-RPC/MCP layer is hand-written and minimal. Careful data-quality handling (team-name canonicalisation with state suffixes, accent folding, multi-format dates, cross-file de-duplication via a "primary source" per competition/season). Answers phrased as formatted text for LLM consumption.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
