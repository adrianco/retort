# Summary: language=erlang_model=sonnet_prompt=ATDD · rep 1

- **Shape:** Erlang/OTP escript MCP server (JSON-RPC 2.0 over stdio) with an in-memory dataset loaded into `persistent_term`; hand-written CSV parser, no external deps.
- **Structure:** 4 source modules + 1 app.src, 1 Common Test suite (15 acceptance cases).
- **Interfaces:** 3 MCP methods (`initialize`, `tools/list`, `tools/call`) exposing 6 query tools; no HTTP/CLI.
- **Notable:** Zero third-party dependencies — uses OTP's built-in `json` module and a bespoke CSV parser. Tests are written purely against the MCP protocol surface (ATDD-style). All 5 match CSVs + FIFA players loaded; BR-Football tournaments deliberately namespaced (`serie_a_stats`, etc.) to avoid double-counting with the primary Brasileirão set.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
