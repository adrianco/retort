# Architecture Summary — brazilian_soccer_mcp (rep2, m80)

> Generated inline (the `run-summary` skill was not available as an invocable skill in this
> session). Covers modules, interfaces, and data flow.

## Package layout

```
brazilian_soccer_mcp/
  __init__.py            (3 lines)   package marker
  data_loader.py         (246)       CSV loading, caching, team-name normalization, date parsing
  match_queries.py       (293)       MatchQueryEngine — find/format matches, head-to-head, team history
  team_queries.py        (236)       TeamQueryEngine — team stats, home/away records, competitions
  player_queries.py      (207)       PlayerQueryEngine — search/filter FIFA players, ratings
  competition_queries.py (195)       CompetitionQueryEngine — standings, champion, cup bracket
  statistical_analysis.py(292)       StatisticalAnalysisEngine — avg goals, win rate, biggest wins, trends
  server.py              (266)       BrazilianSoccerMCP — string-method dispatcher over the engines
tests/
  test_brazilian_soccer_mcp.py (392) 41 pytest tests across 9 classes
```

## Interfaces

- **`BrazilianSoccerMCP.handle_request(method, params)`** is the single entrypoint. It
  dispatches ~19 dotted method names (`match.find`, `team.get_statistics`,
  `player.search`, `competition.get_standings`, `stats.get_average_goals`, …) to the five
  engine objects and wraps exceptions into `{'error': ...}`.
- Each engine holds its own `DataFileManager` and lazily loads/caches DataFrames.

## Data flow

`data/kaggle/*.csv` → `DataFileManager.load_dataframe` (utf-8 → latin-1 fallback, column
strip, cached) → `get_all_matches()` concatenates the 5 match CSVs (union of columns) →
engines filter/aggregate over the combined frame → dicts returned to `handle_request`.

## Key observations

- The "MCP server" is a **plain Python dispatch class** — no `mcp` SDK import, no
  JSON-RPC/stdio transport, no tool schemas, and no runnable entrypoint (`__main__`). It is
  MCP-*shaped* (named methods + params) but not an MCP-protocol server.
- The combined match frame is heterogeneous: the Brasileirão/Cup/Libertadores/historical
  CSVs expose `home_team`/`away_team`, while `BR-Football-Dataset.csv` uses `home`/`away`.
  Team filters in `find_matches` only test `home_team`/`away_team`, so the 10k-row extended
  dataset is effectively excluded from team-scoped searches.
- No dependency manifest (`requirements.txt`/`pyproject.toml`); pandas + pytest are implicit.
