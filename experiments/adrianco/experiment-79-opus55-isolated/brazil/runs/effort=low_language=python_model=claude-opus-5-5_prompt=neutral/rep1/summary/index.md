# Architecture summary

Brazilian Soccer MCP server, pure Python standard-library (no third-party deps).

## Modules (`brazilian_soccer/`)

- **`normalize.py`** — team-name/competition normalisation: state-suffix stripping,
  accent folding (`fold`), a `TeamRegistry` for fuzzy team resolution, multi-format
  date parsing (`parse_date`, `parse_datetime`), competition canonicalisation, club→state
  and known-club tables, `LEAGUES` set.
- **`data.py`** — CSV loading. `load_matches` reads all 5 match CSVs into a unified
  `Match` dataclass, de-duplicates fixtures that recur across files (merging `sources`),
  infers season for the pandemic-shifted 2020 campaign, and returns a per-file load report.
  `load_players` reads `fifa_data.csv` into tidy dicts (skills, ratings, physique).
- **`service.py`** — `SoccerData` knowledge base: the query layer. Match filtering
  (`find_matches`), team records (`team_stats`), head-to-head, standings/table computed
  from results, season summaries (league champion/relegation and inferred cup finals),
  aggregate `competition_stats`, `rank_teams`, `biggest_wins`, derbies, player search
  and per-club aggregation, cross-file `team_profile`. Argument resolution raises
  `QueryError` on bad input. Process-wide cached `load_default()`.
- **`server.py`** — MCP layer. JSON-RPC 2.0 over stdio (`serve`/`handle_message`),
  `initialize` with protocol-version negotiation, `tools/list`, `tools/call`, `ping`.
  17 tools registered via a `@tool` decorator, each returning LLM-quotable text.

## Flow

stdin JSON-RPC → `handle_message` → `call_tool` (arg validation) → tool handler →
`SoccerData` query → formatted text → JSON-RPC response on stdout.

## Tests (`tests/`, 61 functions)

`test_normalize`, `test_data_loading`, `test_matches`, `test_players`,
`test_teams_and_competitions`, `test_server` (MCP protocol handshake, tools/list,
tools/call, error codes, notifications). `conftest.py` provides a shared loaded `db`.
