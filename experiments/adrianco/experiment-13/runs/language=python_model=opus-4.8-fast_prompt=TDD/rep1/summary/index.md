# Summary: language=python · model=opus-4.8-fast · prompt=TDD · rep 1

- **Shape:** Python MCP server (FastMCP/stdio) over an in-memory knowledge graph built from 6 bundled Kaggle CSVs of Brazilian soccer data.
- **Structure:** 7 source modules + 5 test files (68 test functions), clean layering: `normalize` → `data_loader` → `queries` → `server`/`demo`.
- **Interfaces:** 0 HTTP routes / 7 MCP tools / ~15 exported functions+classes.
- **Notable:** Strong separation of concerns and a non-trivial fixture-deduplication layer for overlapping source files (preferring played copies, guarding against over-merge of distinct legs). Output formatting is split from query logic so the engine is independently testable.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
