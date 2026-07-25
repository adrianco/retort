# Summary: go · claude-opus-5 · neutral · rep 1

- **Shape:** Go MCP (Model Context Protocol) server over stdio, built on the official `modelcontextprotocol/go-sdk`, serving a read-only in-memory knowledge graph loaded from six Kaggle CSVs of Brazilian soccer data.
- **Structure:** 12 non-test source files + a shared `internal/bdd` test harness, across `main` and two internal packages (`mcpserver`, `soccer`); 5 test files using a Given/When/Then BDD style.
- **Interfaces:** 0 HTTP routes; 18 MCP tools + 2 MCP resources; a single CLI binary with 7 flags (`-check`, `-list-tools`, `-tool`/`-args`, `-data`, `-quiet`).
- **Notable:** Substantial, well-factored implementation — dedicated name-normalization + resolver layers (accents, state suffixes, curated club/rivalry tables), all standings/records/aggregates *computed* from match results rather than stored, and CLI tool calls routed through a real in-memory MCP round trip so they exercise the same code path as a live host.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
