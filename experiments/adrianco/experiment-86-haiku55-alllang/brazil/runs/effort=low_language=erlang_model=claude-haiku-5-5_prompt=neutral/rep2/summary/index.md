# Summary: effort=low language=erlang model=claude-haiku-5-5 prompt=neutral · rep 2

- **Shape:** Erlang/OTP MCP server (stdio JSON-RPC 2.0) over the Brazilian soccer datasets, using only OTP built-ins (`json`, `persistent_term`) — zero external deps.
- **Structure:** 10 source modules + 1 header, 4 EUnit test files (72 tests, all passing).
- **Interfaces:** 4 MCP methods + 7 query tools with JSON Schemas; no HTTP/DB — data loaded eagerly into `persistent_term`.
- **Notable:** Strong domain handling — RFC 4180 CSV parser, accent/case folding, team-name normalisation with aliases and UF/country-code states, cross-source de-duplication, and BDD tests that reproduce the spec's exact 2019 Brasileirão table (Flamengo 90 pts, 28 W).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
