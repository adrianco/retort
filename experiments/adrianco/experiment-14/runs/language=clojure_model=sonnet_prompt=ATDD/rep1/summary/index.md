# Summary: language=clojure_model=sonnet_prompt=ATDD · rep 1

- **Shape:** Clojure MCP server (hand-rolled JSON-RPC 2.0 over stdin/stdout via cheshire) with an in-memory CSV-backed query layer for Brazilian soccer data.
- **Structure:** 4 source modules (core / data / tools / normalize), 2 test files (23 deftest vars, 111 assertions).
- **Interfaces:** 4 JSON-RPC methods, 6 MCP tools, 6 CSV datasets loaded into in-memory maps.
- **Notable:** Clean separation of protocol (core) / query logic (tools) / data loading (data) / name canonicalization (normalize). Acceptance tests (ATDD) target the `tools/*` API directly rather than the JSON-RPC protocol layer, and share one preloaded full dataset instead of starting each scenario from an empty system.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
