# Summary: go · hermes-local · Qwen3-Coder-Next-4bit (m80) · rep 2

- **Shape:** Go in-memory soccer query library with tool-shaped handlers — but **not an MCP server** (no MCP SDK, no transport, zero dependencies).
- **Structure:** 4 source modules (main/data/query/model), 2 test files, 32 test functions.
- **Interfaces:** 0 MCP tools registered / 0 HTTP routes / 10 exported `Handle*` methods over 15+ query functions.
- **Notable:** Solid, well-factored query engine that reads all 6 provided CSVs and computes stats/standings/H2H — but the headline requirement (MCP protocol) is unmet: handlers exist only as uncalled Go methods, and `Run()` starts no server. Head-to-head goals-for tally is miscounted when the first team plays away.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
