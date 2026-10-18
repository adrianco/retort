# Summary: effort=low_language=clojure_model=claude-haiku-5-5_prompt=neutral · rep 2

- **Shape:** Zero-dependency Clojure MCP server (JSON-RPC 2.0 over stdio) over the Brazilian soccer Kaggle CSVs, with its own CSV parser, JSON codec, and name normalization.
- **Structure:** 7 source modules, 6 test namespaces + 1 test runner (893 src LOC / 363 test LOC).
- **Interfaces:** 4 MCP methods (initialize, ping, tools/list, tools/call) exposing 7 query tools; no HTTP/CLI surface beyond the stdio server.
- **Notable:** No external deps at all — CSV and JSON are hand-written; data loaded eagerly at startup; the BR-Football dataset is deliberately de-duplicated against the primary files; name normalization handles accents, state suffixes, and club aliases.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
