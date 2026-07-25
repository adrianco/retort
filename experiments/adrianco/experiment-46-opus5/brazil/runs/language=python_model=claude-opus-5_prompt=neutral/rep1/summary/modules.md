# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer/__init__.py | Package marker / version | — |
| brazilian_soccer/server.py | FastMCP server; 24 `@mcp.tool()` query tools + 2 resources over stdio | `mcp`, `main()`, `get_graph()`, tool fns (`search_matches`, `head_to_head`, `standings`, `search_players`, …) |
| brazilian_soccer/queries.py | Query layer — every question the server answers, returns JSON-friendly dicts | `search_matches`, `last_meeting`, `head_to_head`, `team_stats`, `team_profile`, `compare_teams`, `search_players`, `player_profile`, `club_squad`, `standings`, `competition_summary`, `knockout_bracket`, `biggest_wins`, `team_rankings`, `home_away_split`, `derbies`, `overall_statistics` |
| brazilian_soccer/loader.py | Reads the six Kaggle CSVs, cross-source de-dup/merge, builds Dataset | `load_dataset()`, `resolve_data_dir()`, `Dataset`, `MatchCollector` |
| brazilian_soccer/graph.py | In-memory knowledge graph (nodes/edges) + lookup indexes over the Dataset | `KnowledgeGraph`, `load_graph()`, `Node` |
| brazilian_soccer/models.py | Dataclasses + aggregation helpers | `Team`, `Match`, `Player`, `TeamRecord` |
| brazilian_soccer/normalization.py | Accent/slug handling, date/int/time parsing, competition + curated-club normalization | `slugify`, `parse_date`, `parse_int`, `parse_time`, `normalize_competition`, `parse_team_name`, `lookup_curated` |
| brazilian_soccer/teams.py | Team-name registry: observe raw spellings → canonical ids, fuzzy search | `TeamRegistry` (`observe`, `build`, `team_id_for_raw`, `resolve`, `search`) |
| brazilian_soccer/formatting.py | Renders each query dict into human-readable text for the LLM | `format_matches`, `format_standings`, `format_head_to_head`, `format_players`, … (22 formatters) |
| brazilian_soccer/demo.py | Answers the spec's sample questions from the CLI | `main()`, `answer()` |
| tests/conftest.py | Session fixtures: real `graph`/`dataset`, `synthetic_graph`, `fastest` timer | fixtures |
| tests/test_*.py (13 files) | 158 test functions across loader, graph, normalization, registry, all query families, server, stdio integration, performance, sample questions | test functions |

Build artifacts (`__pycache__`, `*.egg-info`) excluded.
