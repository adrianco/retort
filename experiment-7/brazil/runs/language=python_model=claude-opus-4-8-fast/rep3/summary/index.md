# Summary: language=python_model=claude-opus-4-8-fast · rep 3

- **Shape:** Python MCP server (FastMCP) over an in-memory knowledge-graph query engine; stdlib-only data layer reading six Kaggle CSVs.
- **Structure:** 7 source modules + conftest, 8 test files (71 test functions).
- **Interfaces:** 13 MCP tools / 0 HTTP routes / ~16 exported `KnowledgeGraph` query methods.
- **Notable:** Cross-dataset team-name normalization and source-priority fixture deduplication; import-guarded `mcp` so engine+tests run without the package; computes standings/stats from matches rather than hardcoding.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
