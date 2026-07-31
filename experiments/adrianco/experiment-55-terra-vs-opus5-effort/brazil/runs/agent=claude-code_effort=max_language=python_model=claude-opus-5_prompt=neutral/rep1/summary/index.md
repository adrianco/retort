# Architecture Summary: brazilian_soccer MCP server

A knowledge-graph MCP server over six Kaggle Brazilian-soccer CSVs. Layered
design, ~5.3k LOC source + ~3.0k LOC tests.

## Modules (`brazilian_soccer/`)

| Module | LOC | Role |
|--------|-----|------|
| `loaders.py` | 671 | Parses the six CSVs into `Match`/`Player` records; dedups the three overlapping Brasileirão sources; UTF-8/BOM + multi-format date handling. |
| `models.py` | 292 | Dataclasses: `Match`, `Player`, `TeamNode`, `TeamRecord`, graph node types. |
| `graph.py` | 454 | `KnowledgeGraph` — builds team/player/competition nodes + edges from loaded records; lazy `.load(data_dir)`; nationality/club/team indexes. |
| `names.py` | 1054 | Team-name normalization (state suffixes, aliases, accents, nicknames like "Timão"/"Fla"). |
| `queries.py` | 1328 | The query layer: `find_matches`, `head_to_head`, `team_stats`, `standings`, `knockout_bracket`, `search_players`, `team_rankings`, `biggest_wins`, `derbies`, `compare_seasons`, `competition_stats`, etc. |
| `formatting.py` | 716 | Renders query dicts to human/LLM-readable text. |
| `server.py` | 450 | MCP server (`build_server`) registering 17 `@server.tool()` handlers; works with mcp 1.x FastMCP and 2.x MCPServer; stdio transport via `main`. |
| `cli.py` / `demo.py` | 260 | Local CLI + scripted demo over the same query layer. |

## Flow

CSV files → `loaders` → `graph.KnowledgeGraph` (in-memory, built once, ~1s) →
`queries` (pure filters/aggregations) → `formatting` → MCP tool text response.
Standings and head-to-head records are **computed** from match results, not
hardcoded.

## Tests (`tests/`)

13 test modules, 172 test functions, exercising loaders, graph, each query
family (matches/teams/players/competitions), names, formatting, server tool
registration, CLI, demo, and a `performance` suite asserting the 2s/5s budgets.
One data-guard skip in `conftest.py` (skips only if the CSV dir is absent).
