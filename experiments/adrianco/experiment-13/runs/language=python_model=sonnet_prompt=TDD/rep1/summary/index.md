# Architecture Summary

Brazilian Soccer MCP Server (Python, FastMCP). Layered design: a data-loading
layer normalizes heterogeneous CSV datasets into a common match schema, four
query modules implement the analytics, and `server.py` exposes them as MCP tools.

## Modules

| Module | Responsibility |
|--------|----------------|
| `data_loader.py` | Loads 6 CSVs from `data/kaggle/`, normalizes team names (state-suffix handling), parses mixed/BR date formats, projects each source to a common schema (`home_team, away_team, home_goal, away_goal, date, competition, season`), and concatenates into `all_matches`. `DataLoader` eagerly loads all sources; FIFA player data loaded separately. |
| `match_queries.py` | Match filters: by team (home/away/either), head-to-head between two teams, by season, by competition, by date range; plus result formatting and a H2H W/D/L summary. |
| `team_queries.py` | Per-team aggregates: W/D/L record, goals for/against, separate home/away records, top-scoring and best home/away tables. |
| `player_queries.py` | FIFA player search by name/nationality/club/position, top-rated filtering, and Brazilian-club roster aggregation. |
| `competition_queries.py` | Standings computed from match results (3-1-0 points, GD tiebreak), biggest wins, avg goals/match, home win rate, season summary. |
| `server.py` | `handle_*` functions (unit-testable, called directly by tests) wrapped by `@mcp.tool()` definitions. `lru_cache`'d `DataLoader`. 11 MCP tools. |

## Data flow

CSV files → per-source loaders → `_to_common` projection → `pd.concat` →
`DataLoader.all_matches` → query modules (pandas filtering/aggregation) →
`handle_*` formatters → MCP tool string responses.

## Tests

6 test modules (one per source module), 181 test functions, pandas-based
fixtures exercising the real datasets. No skips/xfail. Mirrors the TDD prompt:
each source module has a co-designed test module.
