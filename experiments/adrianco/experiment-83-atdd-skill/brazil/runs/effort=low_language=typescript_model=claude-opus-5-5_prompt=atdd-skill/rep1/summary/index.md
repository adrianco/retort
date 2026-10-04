# Summary: effort=low language=typescript model=claude-opus-5-5 prompt=atdd-skill · rep 1

- **Shape:** TypeScript MCP server (`@modelcontextprotocol/sdk`) over stdio, backed by in-memory CSV data, with a zod-validated tool surface.
- **Structure:** 5 source modules, 3 test modules (spec / DSL / protocol driver), 499 LOC src + 288 LOC test.
- **Interfaces:** 14 MCP tools, 0 HTTP routes, 0 CLI subcommands; 6 CSV data sources.
- **Notable:** Clean ATDD four-layer test architecture (domain-language spec → DSL → MCP-over-stdio driver → real server through its public interface). Data layer does non-trivial work: multi-format date parsing, team-name normalisation, cross-source dedup, and per-season preferred-source selection for league tables.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
