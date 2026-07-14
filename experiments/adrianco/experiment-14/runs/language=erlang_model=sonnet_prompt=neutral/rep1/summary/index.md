# Architecture Summary — Brazilian Soccer MCP Server (Erlang)

Generated inline by `evaluate-run` (the `run-summary` skill is not registered as
an invocable Skill in this session).

## Modules

| Module | Role |
|--------|------|
| `brazilian_soccer_mcp` | escript entrypoint (`main/1` → `bsm_mcp_server:start/0`). |
| `brazilian_soccer_mcp_app` / `_sup` | OTP application + supervisor scaffolding. |
| `bsm_mcp_server` | MCP/JSON-RPC stdio loop: `initialize`, `tools/list`, `tools/call`, `ping`. Defines 8 tools and formats results to text. Test-friendly wrappers (`*_test/…`) bypass I/O. |
| `bsm_csv` | Streaming CSV parser — handles quotes, escaped quotes, BOM, CRLF; returns list of header→value maps. |
| `bsm_data` | Loads all 6 CSVs into ETS (`bsm_matches`, `bsm_players`, `bsm_stats_matches`), normalizes rows, strips `-UF` state suffixes, parses ISO + Brazilian dates. |
| `bsm_query` | Pure query layer over the ETS data: `search_matches`, `get_team_stats`, `head_to_head`, `search_players`, `get_standings`, `get_biggest_wins`, `get_season_summary`, `get_competition_matches`. |

## Data flow

`start/0` → `bsm_data:load_all/0` (CSV → normalize → ETS) → JSON-RPC loop reads
stdin, dispatches `tools/call` to `bsm_query`, formats the returned map to MCP
text content, writes JSON to stdout via `thoas`.

## Notes

- Match competitions: `brasileirao`, `brasileirao_hist`, `copa_brasil`,
  `libertadores` all flow through `get_matches/0`.
- `bsm_stats_matches` (BR-Football-Dataset.csv, corners/shots/attacks) is loaded
  but **never read** by any query tool — see findings.
