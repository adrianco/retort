# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Data model, CSV loading, and all query logic (matches, team records, head-to-head, standings, players, stats) | `Database`, `Match`, `Player`, `Record`, `Standing`, `normalize()`, `format_match()` |
| src/main.rs | JSON-RPC (stdio) MCP server: dispatch `initialize`/`tools/list`/`tools/call`, define 7 tools | `main()`, `tools()`, `result()` |

Tests live inline in `src/lib.rs` under `#[cfg(test)] mod tests` (3 test functions).
Non-source files skipped: `Cargo.lock`, `target/`, `data/kaggle/*.csv`.
