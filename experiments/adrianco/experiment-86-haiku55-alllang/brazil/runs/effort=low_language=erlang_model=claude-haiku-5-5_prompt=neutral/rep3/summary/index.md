# Summary: effort=low language=erlang model=claude-haiku-5-5 prompt=neutral · rep 3

- **Shape:** Erlang/OTP MCP server (JSON-RPC 2.0 over stdio) with an in-memory dataset loaded from the Kaggle CSVs; pure query layer, hand-rolled CSV parser, zero external dependencies.
- **Structure:** 7 source modules (+ app.src), 8 test modules, 73 EUnit tests.
- **Interfaces:** 4 JSON-RPC methods, 7 MCP tools, 1 escript CLI entry; match() + player() data schemas.
- **Notable:** Clean concern separation (protocol / tools / query / data / csv / text); no dependencies at all — uses OTP's built-in `json` module and its own RFC 4180 CSV parser; careful team-name normalisation with state-suffix disambiguation and accent folding; dedupe reconciles the same fixture appearing across multiple files.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
