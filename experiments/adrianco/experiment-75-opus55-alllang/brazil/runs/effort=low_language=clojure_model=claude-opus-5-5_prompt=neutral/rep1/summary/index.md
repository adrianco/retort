# Summary: effort=low_language=clojure_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Clojure MCP server (hand-rolled JSON-RPC 2.0 over stdio) over 6 Kaggle CSVs, with a query/stats layer and a BDD test suite.
- **Structure:** 3 source modules (data / query / server), 1 test file (25 scenarios, 76 assertions), 884 LOC total.
- **Interfaces:** 4 MCP methods (initialize, ping, tools/list, tools/call) + 13 tools; in-memory match/player data schema.
- **Notable:** Careful team-name normalization (accent-stripping, state-suffix disambiguation, alias table, cross-file fixture dedup within a 3-day window); single-source-per-season standings to avoid double-counting; tests assert exact dataset row counts and known championship outcomes (Flamengo 2019 = 90 pts, Cruzeiro 2003).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
