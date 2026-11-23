# Summary: agent=codex effort=low language=rust model=gpt-6.2-astra prompt=neutral · rep 1

- **Shape:** Rust MCP stdio server exposing one `query_soccer(sql)` tool over an in-memory SQLite DB built from the 6 Kaggle CSVs.
- **Structure:** 3 Rust source files + 1 SQL file (433 lines total), 1 test file (2 tests / 21 scenarios).
- **Interfaces:** 4 JSON-RPC methods, 1 MCP tool, 3 base tables + 2 views, 2 custom SQL functions.
- **Notable:** Unusually terse, idiomatic Rust. Rather than one tool per query category, it exposes a single read-only SQL endpoint plus a rich schema description, and reconciles duplicate match rows across 5 overlapping CSVs into a deduplicated `matches` table — a more sophisticated data model than the task strictly requires.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
