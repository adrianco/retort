# Summary: mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80 · rep 1

- **Shape:** FastMCP tool server (12 tools) plus a parallel FastAPI HTTP app, both over an in-memory pandas-loaded CSV store of Brazilian soccer data.
- **Structure:** 6 source modules + 3 test files (54 test functions total across `test_api.py` and `test_mcp.py`).
- **Interfaces:** 12 MCP tools / 12 HTTP routes / 3 dataclass models with `to_dict()`; all query logic centralized in one `QueryEngine`.
- **Notable:** Dual MCP+REST surface over a single query engine is more complete than the spec strictly requires. Data is reloaded and reparsed from all six CSVs on every tool call / request (no caching), team matching is case-insensitive substring on normalized names, and `Match.id` is never populated so ID lookups always miss. Declared Pydantic request models in `api.py` are unused.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
