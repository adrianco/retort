# Architecture Summary

> `run-summary` skill not invoked separately; this is an inline architecture note.

## Package: `brazilian_soccer_mcp/`

| Module | Role |
|--------|------|
| `data_loader.py` | `DataLoader` — loads all 6 CSVs from `data/kaggle/`, normalizes team names (strips `-SP`/`(URU)` suffixes), parses multiple date formats, exposes `get_all_matches()` (concatenates all match sources with a `competition` column) and `get_all_players()`. Singleton via `get_data_loader()`. |
| `match_queries.py` | `MatchQueryHandler` — find by team (home/away/either), by two teams, by date range, by competition, by season; match details & outcome analysis. |
| `team_queries.py` | `TeamQueryHandler` — W/L/D + goals-for/against aggregation, home/away split, head-to-head, competition history, top-scorers (from FIFA club match), all-teams/by-state. |
| `player_queries.py` | `PlayerQueryHandler` — search by name/nationality/club/position, Brazilian-player filters, ratings/attributes. |
| `competition_queries.py` | `CompetitionQueryHandler` — standings computed from match results, champion, relegation zone, cup bracket, biggest victories, competition summary (avg goals, home-win rate). |
| `server.py` | **Flask** app exposing REST endpoints (`/health`, `/status`, `/query`, `/team/<name>`, `/player/<name>`, `/standings`, ...). Wires the four handlers over the singleton loader. |

## Flow

`server.get_handlers()` lazily builds the singleton `DataLoader` (reads CSVs from `../data/kaggle`) and the four query handlers, then routes HTTP requests to handler methods and returns JSON.

## Note on "MCP"

Despite the naming/docstrings, there is **no MCP-protocol implementation** — no `mcp` SDK import, no tool/resource registration, no stdio server. The interface is a plain Flask HTTP/REST API. See `findings.jsonl` R1.
