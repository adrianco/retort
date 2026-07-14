# Summary: language=elixir_model=sonnet_prompt=ATDD · rep 1

- **Shape:** Elixir/OTP MCP server (hand-rolled JSON-RPC over stdio) with a GenServer + ETS data store over 6 Brazilian-soccer CSVs.
- **Structure:** 12 source modules, 2 test files (27 acceptance + 1 smoke).
- **Interfaces:** 0 HTTP routes / 5 MCP tools / 4 MCP protocol methods.
- **Notable:** Acceptance suite drives the design and exercises the server only through the MCP `tools/call` protocol (matching the ATDD prompt). Data loaded into ETS at startup; queries are full-table scans. No external MCP SDK dependency — only `jason` + `nimble_csv`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
