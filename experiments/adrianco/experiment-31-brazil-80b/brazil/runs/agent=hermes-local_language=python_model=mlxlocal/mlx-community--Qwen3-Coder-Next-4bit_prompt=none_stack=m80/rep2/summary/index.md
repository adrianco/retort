# Run Summary: Brazilian Soccer "MCP" Server

## Surface

A Python knowledge-graph query library over pre-downloaded Kaggle Brazilian-soccer
CSV datasets. It exposes ~24 query handlers for matches, teams, players,
competitions, and aggregate statistics, plus a heuristic natural-language
`answer_question` router. Despite the naming, it is a plain in-process Python API,
**not** an MCP-protocol server (no MCP SDK, transport, or tool schemas).

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `soccer_mcp/server.py` | Facade wiring loader + query classes; `execute_query` dispatch, NL `answer_question` | `SoccerMCPServer`, `execute_query()`, `answer_question()` |
| `soccer_mcp/loader.py` | Loads & normalizes 6 CSVs into `Match`/`Player` objects; team-name normalization | `DataLoader`, `load_all_data()`, `get_matches_by_*`, `get_head_to_head()` |
| `soccer_mcp/queries.py` | 24 query implementations across 5 classes | `MatchQueries`, `PlayerQueries`, `CompetitionQueries`, `TeamQueries`, `StatisticalAnalysis` |
| `soccer_mcp/models.py` | Dataclasses for `Match`, `Player`, `TeamStats`, `QueryResult` | model types |
| `tests/test_soccer_mcp.py` | unittest suite | 38 test functions (2 classes) |

## Flow

`SoccerMCPServer.__init__` → `DataLoader.load_all_data()` loads all 6 CSVs
(23,954 matches, 18,207 players) into memory and builds a team-name mapping →
five query-handler classes are constructed and registered in a `handlers` dict →
callers invoke `execute_query(name, **kwargs)` which dispatches to a handler
returning a `QueryResult`, or `answer_question(str)` which keyword-routes NL
questions to a handler.

## Notes

- Standings (`get_competition_standings`) and head-to-head (`get_head_to_head`)
  are genuinely computed from match results, not hardcoded.
- `queries.py` is a 1445-line monolith (5 classes) — drives the low
  maintainability score (0.30).
- No `requirements.txt`/`pyproject.toml`; relies only on the Python stdlib
  (`csv`, `re`, `collections`) — no third-party deps.
