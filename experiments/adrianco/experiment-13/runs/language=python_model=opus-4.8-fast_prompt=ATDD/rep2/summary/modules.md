# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer_mcp/server.py | MCP server; registers the 10 query tools (the only public interface) | `create_server()`, `main()` |
| brazilian_soccer_mcp/repository.py | Query/domain logic over loaded matches & players (filters, records, standings, stats, player search) | `SoccerRepository`, `.from_dir()` |
| brazilian_soccer_mcp/data_loader.py | Parses the 6 Kaggle CSVs into domain models; tolerant of missing cols; dedups overlapping sources | `load_dataset()` |
| brazilian_soccer_mcp/normalize.py | Team-name cleaning, accent stripping, competition canonicalization, multi-format date parsing | `team_key()`, `clean_team_name()`, `canonical_competition()`, `parse_date()`, `text_key()` |
| brazilian_soccer_mcp/models.py | `Match` / `Player` dataclasses with `to_dict()` JSON serialization | `Match`, `Player` |
| brazilian_soccer_mcp/__init__.py | Package exports | `create_server` |
| tests/conftest.py | ATDD harness: `SoccerSystem` builder + in-memory MCP client (`ToolClient`); seeds isolated temp datasets | `soccer_system` fixture |
| tests/acceptance/test_match_queries.py | Match-query acceptance scenarios | 6 test functions |
| tests/acceptance/test_player_queries.py | Player-query acceptance scenarios | 7 test functions |
| tests/acceptance/test_competition_queries.py | Standings/winner/list-competitions scenarios | 5 test functions |
| tests/acceptance/test_team_queries.py | Team record + head-to-head scenarios | 4 test functions |
| tests/acceptance/test_statistics.py | Aggregate-statistics scenarios | 4 test functions |
| tests/acceptance/test_data_quality.py | Name/accent/date normalization + dedup + cross-file scenarios | 6 test functions |
| tests/acceptance/test_server_protocol.py | Tool advertisement + empty-system behavior | 4 test functions |
| tests/unit/test_repository.py | Unit TDD under the acceptance suite | 4 test functions |
| tests/unit/test_normalize.py | Normalization unit tests | 10 test functions |
