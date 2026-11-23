# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| soccer.hpp | Shared declarations: `string` alias, RAII `Statement`, `prepare()`, `load()` decl | `prepare()`, `load()` |
| data.cpp | CSV import + in-memory schema build (tables, views, normalization UDFs) | `load()`, `team()`/`fold()` SQL functions |
| server.cpp | MCP JSON-RPC 2.0 stdio server; single `query_soccer` SQL tool; `main()` | `main()`, `serve()`, `query()`, `toolsList()` |
| test_soccer.py | End-to-end MCP stdio integration tests | 4 test methods (`SoccerScenarios`) |
| Makefile | Build (`make`) and test (`make test`) via pkg-config | `soccer-mcp`, `test` targets |
| README.md | Build/run instructions, data provenance, coverage notes | — |

Build artifacts (`soccer-mcp` binary) and data (`data/kaggle/*.csv`) excluded.
