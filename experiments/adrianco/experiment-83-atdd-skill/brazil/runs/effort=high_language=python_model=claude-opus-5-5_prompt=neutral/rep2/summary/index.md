# Summary: effort=high language=python model=claude-opus-5-5 prompt=neutral · rep 2

- **Shape:** Python MCP server (`mcp` SDK + pydantic) exposing an in-memory Brazilian-soccer query engine over 17 tools + 1 resource (stdio / streamable-HTTP).
- **Structure:** 4 source modules (~2087 LOC) + 6 test files (~762 LOC, 71 test fns → 182 parametrized cases).
- **Interfaces:** 17 MCP tools, 1 MCP resource, 0 HTTP routes / CLI subcommands (CLI is just a transport selector).
- **Notable:** Heavy emphasis on team-name normalization and cross-dataset joins; standings computed from match results; a genuine out-of-process stdio end-to-end test; deliberately no external APIs. Far richer tool surface than the spec's minimum.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
