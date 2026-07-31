# Architecture Summary

Brazilian Soccer MCP server implemented as a Python package `brazilian_soccer/` with a clean layered design.

## Modules

| Module | Responsibility |
|--------|----------------|
| `loader.py` (504 L) | Reads the six CSVs in `data/kaggle/`, parses multiple date formats, builds `Match`/`Player` objects, deduplicates overlapping Série A datasets. |
| `models.py` (206 L) | `Match` and `Player` dataclasses with `to_dict`, derived fields (winner, total goals). |
| `names.py` (282 L) | Team-name normalization (strips state suffixes, accents, official long names) and display-name resolution. |
| `graph.py` (777 L) | `KnowledgeGraph` — the query engine. Indexes matches/players; methods: `find_matches`, `head_to_head`, `team_stats`, `standings`, `competition_summary`, `statistics`, `biggest_wins`, `search_players`, `player_profile`, `players_by_brazilian_club`. |
| `formatters.py` (164 L) | Renders query results into human-readable text blocks. |
| `server.py` (518 L) | MCP server — ~20 tool wrappers, `dispatch`, `tool_definitions`, `build_server` using the `mcp` SDK (`Server`, `Tool`, stdio transport). |

## Flow

`server.main()` → `load_all()` builds a `KnowledgeGraph` → MCP `on_call_tool` → `dispatch(name, args)` → graph method → `formatters` → `TextContent` result.

## Tests

`tests/` holds 74 test functions across loading/names, queries, MCP server, and performance/formatting, plus a Gherkin `features.feature`. Two conditional `pytest.skip` guards fire only if the dataset directory is absent (not triggered here — `test_coverage=1.0`).
