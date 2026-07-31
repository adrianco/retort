# Modules

Package `brazilian_soccer/` — a layered, in-memory knowledge-graph MCP server. Layers bottom-up: config → text → teams → models → loaders → graph → queries → formatting → tools → server/cli.

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer/__init__.py | Package docstring + lazy re-export shim | `__version__`, `load_knowledge_graph`, `KnowledgeGraph` (via `__getattr__`) |
| brazilian_soccer/config.py | Data-dir location and the six-CSV dataset catalogue | `DatasetSpec`, `DATASETS`, `DATASETS_BY_KEY`, `data_dir()`, `dataset_path()`, `missing_datasets()` |
| brazilian_soccer/text.py | Unicode/date/number/name-normalisation helpers | `normalize_name()`, `slugify()`, `split_qualifier()`, `parse_date()`, `parse_int()`, `parse_float()`, `parse_time()`, `BRAZILIAN_STATES`, `COUNTRY_CODES` |
| brazilian_soccer/teams.py | Canonical club registry; reconciles cross-dataset spellings | `ClubSpec`, `CLUB_SPECS`, `DERBIES`, `Derby`, `TeamRegistry` (`observe/build/resolve_id/lookup/search`), `match_key()` |
| brazilian_soccer/models.py | Domain dataclasses + derived-stat containers | `Team`, `Competition`, `Match`, `Player`, `TeamRecord`, `StandingRow`, `HeadToHead`, `COMPETITIONS` |
| brazilian_soccer/loaders.py | One CSV reader per dataset → `Match`/`Player` | `read_csv()`, `read_all_match_rows()`, `load_matches()`, `load_players()`, `ParsedRow`, `POSITION_GROUPS`, `position_group()` |
| brazilian_soccer/graph.py | In-memory KG (nodes/edges/indexes) + cross-source de-dup | `KnowledgeGraph`, `LoadReport`, `build_knowledge_graph()`, `load_knowledge_graph()`, `deduplicate()` |
| brazilian_soccer/queries.py | Analytical query API (search, records, standings, stats, players) | `search_matches`, `head_to_head`, `team_record`, `team_profile`, `compare_teams`, `standings`, `competition_champion`, `relegated_teams`, `competition_stats`, `biggest_wins`, `best_records`, `search_players`, `player_profile`, `club_squad`, `find_derbies`, `compare_seasons`, `dataset_summary`, `resolve_team`, `resolve_competition`, `TeamNotFound`, `CompetitionNotFound` |
| brazilian_soccer/formatting.py | Render query results as TASK.md answer layouts | `format_matches`, `format_head_to_head`, `format_team_record`, `format_team_profile`, `format_standings`, `format_players`, `format_player_profile`, `format_club_squad`, `format_competition_stats`, `format_compare_teams`, `format_derbies`, `format_dataset_summary` |
| brazilian_soccer/tools.py | Transport-independent tool layer (name → callable) | `TOOLS`, `ToolResult`, `ToolSpec`, `call_tool()`, `list_tools()`, `tool_names()`, `@tool` decorator (24 registered tools) |
| brazilian_soccer/server.py | MCP SDK binding: tools, resources, prompts | `server` (`MCPServer`), `main()`, `annotate_tool_schemas()`, 24 `@server.tool`, 4 `@server.resource`, 2 `@server.prompt` |
| brazilian_soccer/cli.py | argparse CLI mirroring the tool layer | `main()`, `build_parser()` — subcommands `serve`/`tools`/`summary`/`call` |
| tests/conftest.py | Shared fixtures (graph, tmp data dir, BDD glue) | fixtures (no `test_` functions) |
| tests/test_text.py | Unit tests for text helpers | 12 test functions |
| tests/test_teams.py | Registry / name-reconciliation tests | 22 test functions |
| tests/test_models.py | Dataclass + derived-property tests | 18 test functions |
| tests/test_loaders.py | Per-CSV parser tests | 17 test functions |
| tests/test_graph.py | Graph build, indexes, de-duplication | 22 test functions |
| tests/test_queries.py | Query-layer tests (largest suite) | 50 test functions |
| tests/test_formatting.py | Rendering tests | 14 test functions |
| tests/test_tools.py | Tool-layer dispatch tests | 15 test functions |
| tests/test_mcp_server.py | MCP server binding tests | 2 test functions |
| tests/test_cli.py | CLI subcommand tests | 10 test functions |
| tests/test_robustness.py | Malformed-input / edge-case tests | 9 test functions |
| tests/test_sample_questions.py | End-to-end "20 sample questions" tests | 3 test functions |
| tests/test_bdd_scenarios.py | pytest-bdd runner binding all 8 feature files | `scenarios(...)` × 8 (59 scenarios) |
| tests/features/*.feature | Gherkin BDD specs (8 files) | 59 scenarios total |

Data CSVs under `data/kaggle/` (6 files) and doc files (`README.md`, `brazilian-soccer-mcp-guide.md`, `TASK.md`) are inputs/outputs, not source modules.
