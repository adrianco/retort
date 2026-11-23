# Summary: elixir · gpt-6.2-astra · codex · neutral · rep 1

- **Shape:** Elixir stdlib-only MCP server (JSON-RPC 2.0 over stdio) answering Brazilian-soccer queries from the provided Kaggle CSVs.
- **Structure:** 3 lib modules (`Data`, `Query`, `Server`), 1 test file (9 tests), `mix.exs` escript build; zero external dependencies (uses the built-in `JSON` module, Elixir ≥ 1.18).
- **Interfaces:** 5 MCP tools (`team_profile`, `matches`, `players`, `statistics`, `standings`) plus MCP lifecycle methods (`initialize`, `tools/list`, `tools/call`, `ping`).
- **Notable:** Tight, dense implementation — a single generic match-filter pipeline feeds matches/statistics/standings; curated derby list and cross-source match de-duplication (reconciles the same fixture appearing in multiple CSVs by date proximity). All 5 match CSVs + FIFA players loaded.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
