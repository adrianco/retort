# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazsoccer_mcp/__main__.py | CLI entry point; loads data and serves MCP over stdio | `main()` |
| brazsoccer_mcp/mcp_server.py | Minimal JSON-RPC 2.0 MCP server (initialize/ping/tools.list/tools.call) | `MCPServer`, `run()` |
| brazsoccer_mcp/tools.py | Tool definitions (JSON schemas) + text-formatting handlers | `TOOLS`, `call_tool()`, `Tool` |
| brazsoccer_mcp/store.py | In-memory query layer; dedup, team/competition resolution, aggregates | `SoccerData`, `Record`, `HeadToHead`, `StandingRow`, `QueryError` |
| brazsoccer_mcp/loaders.py | CSV loaders for the six Kaggle datasets | `load_all()`, `load_players()`, `LoadReport` |
| brazsoccer_mcp/models.py | Plain dataclasses shared across layers | `Match`, `Player` |
| brazsoccer_mcp/normalize.py | Team-name/date/number normalization and aliasing | `team_key()`, `display_name()`, `parse_date()`, `normalize_text()` |
| tests/conftest.py | Shared fixtures (real dataset + synthetic match builder) | `data` fixture, `make_match()` |
| tests/test_loaders.py | CSV loader tests | 4 test functions |
| tests/test_normalize.py | Normalization helper tests | 11 test functions |
| tests/test_queries.py | Query-layer tests (matches, standings, players, aggregates) | 26 test functions |
| tests/test_tools_and_server.py | Tool handler + MCP protocol tests | 13 test functions |
