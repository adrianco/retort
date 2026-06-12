# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer_mcp/server.py | MCP tool surface (FastMCP); registers 6 query tools over the knowledge base | `create_server()`, `main()` |
| brazilian_soccer_mcp/knowledge_base.py | In-memory query engine answering match/team/player/standings/stats questions | `KnowledgeBase`, `KnowledgeBase.from_directory()` |
| brazilian_soccer_mcp/loader.py | Per-schema CSV loaders → unified `Match`/`Player`; dedup of overlapping sources | `load_matches()`, `load_players()`, `canonical_competition()` |
| brazilian_soccer_mcp/models.py | Domain dataclasses with JSON-friendly `as_dict()` | `Match`, `Player` |
| brazilian_soccer_mcp/normalize.py | Team-name + text normalization (suffixes, accents, aliases) | `normalize_team()`, `key()`, `team_key()`, `strip_accents()` |
| brazilian_soccer_mcp/__init__.py | Package marker | (none) |
| tests/conftest.py | MCP-client fixtures + CSV dataset builder (real Kaggle schemas) | `DatasetBuilder`, `SoccerClient`, `call()`, `call_expecting_error()` |
| tests/test_acceptance.py | Black-box acceptance spec through the MCP interface | 21 test functions |
| tests/test_unit.py | White-box unit tests for normalize/parse/query engine | 7 test functions (3 parametrized) |
| tests/test_real_data.py | End-to-end checks against the real `data/kaggle` CSVs | 6 test functions |
