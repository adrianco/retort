# Run Summary — Brazilian Soccer MCP Server (Erlang)

## Surface

A stdio JSON-RPC 2.0 MCP server over pre-downloaded Kaggle Brazilian-soccer CSVs.
It loads five match datasets plus the FIFA player table, normalizes team names and
dates, and exposes five tools for match search, team/standings records, aggregate
summaries, player search, and a combined club profile.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `soccer_data.erl` | CSV loading, parsing, team/date normalization, cross-file match de-dup | `load/1`, `team/1`, `fold/1`, `date/1`, `competition/1` |
| `soccer_query.erl` | Tool definitions + query engine (filter/aggregate/paginate) | `run/3`, `tools/0` |
| `soccer_mcp.erl` | JSON-RPC 2.0 MCP transport over stdio | `main/0`, `handle/2` |
| `soccer_tests.erl` | EUnit scenario + stdio integration tests | `scenarios_test_/0`, `stdio_utf8_test_/0` |

## Interfaces (MCP tools)

- **matches** — fixtures/scores filtered by team/opponent/venue/season/date-range/competition/stage/round/derby; `order=margin` for biggest wins; paginated.
- **records** — team records & league standings computed from completed fixtures; `rank_by` points/goals/win_rate; venue home/away/either.
- **summary** — played totals, goals-per-match, home-win-rate; `group_by` season or competition.
- **players** — FIFA snapshot search by name/nationality/club/position, sorted by Overall.
- **club_profile** — joins a club's `records` to its FIFA `players` roster.

JSON-RPC methods: `initialize`, `ping`, `tools/list`, `tools/call`, with
notification suppression and `-32700/-32600/-32601/-32602` error paths.

## Data flow

`soccer_data:load/1` reads the 6 CSVs, parses each row into a canonical match map,
merges extended-stats rows into base league rows (keyed by competition/season/teams),
and returns `#{matches, players, raw}`. `soccer_query:run/3` validates args against
each tool's inputSchema, normalizes, filters, aggregates, and paginates. `soccer_mcp`
wraps queries in the JSON-RPC envelope over stdio with UTF-8 handling.
