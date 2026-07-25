# Summary: go · hermes-local · Qwen3-Coder-Next-4bit (m80) · rep 2

- **Shape:** Go in-memory CSV query engine behind an interactive CLI REPL — MCP protocol
  types declared but no MCP server implemented.
- **Structure:** 3 source modules + 1 test file (10 tests), ~1310 source LOC.
- **Interfaces:** 0 MCP tools, 5 CLI commands, ~13 exported query functions (most not
  wired to any surface).
- **Notable:** Solid per-file CSV parsing with header maps and team-name normalization;
  the central deliverable (an MCP server) is stubbed out as a comment, and several
  spec queries (competition filter, head-to-head, date-range) are missing.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
