# Summary: language=elixir_model=sonnet_prompt=neutral · rep 1

- **Shape:** Elixir/OTP MCP server — stdio JSON-RPC 2.0, NimbleCSV ingestion, in-memory GenServer store, 7 query tools.
- **Structure:** 8 source modules, 1 test file (50 tests), 2 deps (jason, nimble_csv).
- **Interfaces:** 7 MCP tools / 5 JSON-RPC methods / ~7 public query functions.
- **Notable:** Clean OTP layering (server → tools → query engine → store → loader); dedicated `TeamNormalizer` handles state suffixes, accents, and aliases; standings computed from matches; de-dups Brasileirão vs historical pre-2012 to avoid double counting.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
