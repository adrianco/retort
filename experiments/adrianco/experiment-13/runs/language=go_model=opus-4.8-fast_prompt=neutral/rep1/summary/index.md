# Summary: language=go · model=opus-4.8-fast · prompt=neutral · rep1

- **Shape:** Go stdlib-only MCP (Model Context Protocol) server over stdio JSON-RPC, with an in-memory knowledge graph built from 6 Brazilian-soccer CSV datasets. Zero third-party dependencies (go.mod has no requires).
- **Structure:** 11 source files (1 `main` package + 1 hand-rolled `mcp` package + 9-file `soccer` package), 6 test files (33 test functions total).
- **Interfaces:** 0 HTTP routes; 1 CLI binary (`-data`, `-demo`); 5 JSON-RPC methods; 12 MCP tools covering match/team/player/competition/statistical queries.
- **Notable:** MCP protocol implemented from scratch (no SDK). Heaviest engineering is in team-name normalization — accent folding, state-suffix disambiguation (Atlético-MG vs Athletico-PR), club aliases, and cross-source de-duplication via `CleanBySource` (keep the most complete source per competition+season). Tools return plain text, not structured JSON. All-in-memory, linear-scan queries, no pagination.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
