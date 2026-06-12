# Summary: language=elixir_model=sonnet_prompt=TDD · rep 1

- **Shape:** Elixir/OTP MCP server (JSON-RPC over stdio) with an ETS-backed in-memory store loaded from Kaggle CSVs.
- **Structure:** 10 source modules, 5 test files (58 tests).
- **Interfaces:** 7 MCP tools + 4 protocol methods; no HTTP/CLI surface beyond the stdio loop.
- **Notable:** Clean layering (protocol → tools → queries → store → loader); pure CSV parsers separated from the GenServer; full-scan linear queries; defensive row parsing drops malformed rows silently.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
