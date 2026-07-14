# Summary: language=python_model=sonnet-4.6_prompt=tdd · rep 1

- **Shape:** FastMCP (stdio) server over pandas — Brazilian soccer knowledge graph exposing 7 query tools.
- **Structure:** 3 source modules + 3 test files (80 tests), 2 runtime deps (mcp, pandas).
- **Interfaces:** 0 HTTP routes / 0 CLI commands / 7 MCP tools backed by 10 QueryEngine methods.
- **Notable:** Clean layered split (loader → engine → server); normalization handled once at load time; strict-TDD test suite covers loaders, engine, and tool registration/integration. Minor packaging defects in `pyproject.toml` (invalid build backend, dangling `server:main` entry point).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
