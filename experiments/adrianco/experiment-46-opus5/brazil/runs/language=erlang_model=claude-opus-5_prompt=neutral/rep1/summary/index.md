# Architecture Summary — bsmcp (Brazilian Soccer MCP Server)

_Generated inline by evaluate-run; the `run-summary` skill is not registered as invocable in this session._

An OTP application (`bsmcp_app`/`bsmcp_sup`) implementing a JSON-RPC MCP server over
stdio for querying Brazilian soccer datasets. ~4,100 LOC of `src/` + ~2,080 LOC of tests.

## Modules

| Module | LOC | Role |
|--------|-----|------|
| `bsmcp_data.erl` | 880 | Dataset loader + in-memory knowledge graph. Parallel-loads the 6 CSVs from `data/kaggle/`, builds team/player registries, normalizes names. |
| `bsmcp_query.erl` | 1063 | Query engine: `search_matches`, `head_to_head`, `team_stats`/`team_profile`, `standings`, `leaderboard`, `biggest_wins`, `competition_stats`, `search_players`, `player_profile`, `club_squad`, `club_ratings`, `list_teams`, `dataset_summary`. |
| `bsmcp_tools.erl` | 397 | MCP tool registry: 14 tool definitions with JSON-schema arg specs, arg coercion, dispatch table. |
| `bsmcp_server.erl` | 252 | JSON-RPC dispatch: `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`, `ping`. |
| `bsmcp_format.erl` | 436 | Human-readable answer formatting (matches, standings, player cards). |
| `bsmcp_names.erl` | 390 | Team-name normalization (state suffixes, full names, accents). |
| `bsmcp_text.erl` | 281 | Text/UTF-8 helpers. |
| `bsmcp_csv.erl` | 165 | CSV parser. |
| `bsmcp_stdio.erl` / `bsmcp.erl` | 67/79 | stdio transport + escript entrypoint. |
| `bsmcp_json.erl` | 43 | JSON encode/decode. |

## Flow

MCP client → stdio → `bsmcp_server:dispatch/3` → `bsmcp_tools` (arg coercion) →
`bsmcp_query` (filter/aggregate over the in-memory graph loaded by `bsmcp_data`) →
`bsmcp_format` → JSON-RPC reply.

## Tests

9 Common Test suites, 80 test cases: match / team / player / competition / statistics
queries, MCP protocol, stdio transport, data quality, and a sample-questions suite.
All pass (`test_coverage=1.0`).
