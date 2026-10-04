# Summary: effort=high language=go model=claude-opus-5-5 prompt=atdd-skill · rep 1

- **Shape:** Go stdio MCP server (hand-rolled JSON-RPC 2.0) answering natural-language Brazilian-soccer questions from the provided Kaggle CSVs via 20 registered tools.
- **Structure:** 13 source modules across `main`, `internal/app`, `internal/mcpserver`, `internal/soccer`; a four-layer acceptance suite (specs → DSL → protocol driver → built binary) plus two unit test files.
- **Interfaces:** 20 MCP tools (match/team/player/competition/statistics queries); in-memory Match/Player/Team model; no HTTP, no persistence, no external APIs.
- **Notable:** reference-quality black-box ATDD suite driving the real binary as a subprocess (hence low line-coverage, 38.4%, despite thorough behavioural testing); honest `docs/atdd-findings.md` records real data limitations (incomplete 2023 season → no champion named); careful team-name normalization and multi-source match dedup.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
