# Summary: language=python · model=sonnet · tooling=beads · rep 1

- **Shape:** FastMCP (MCP) stdio server over pandas; 16 query tools backed by 6 Kaggle CSVs.
- **Structure:** 2 source modules + 1 test module (51 tests), no dependency manifest.
- **Interfaces:** 16 MCP tools / 0 HTTP routes / 0 CLI commands.
- **Notable:** Careful team-name normalization (accents, state suffixes, MG/PR alias disambiguation) and de-dup logic merging historical with modern Brasileirão seasons; tools return formatted strings rather than structured data; matching is substring-based.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
