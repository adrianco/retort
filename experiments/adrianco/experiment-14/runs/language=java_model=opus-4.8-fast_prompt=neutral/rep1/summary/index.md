# Summary: language=java · model=opus-4.8-fast · prompt=neutral · rep 1

- **Shape:** Java MCP server (JSON-RPC 2.0 over stdio) over an in-memory knowledge graph loaded from 6 Kaggle CSVs; Jackson for JSON, hand-rolled CSV parser, no external data store.
- **Structure:** 9 main source files (server / query / data / model / util packages) + 5 test files (35 tests across protocol, query, graph, and name-canonicalization).
- **Interfaces:** 0 HTTP routes / 9 MCP tools (search_matches, head_to_head, team_record, search_players, standings, match_statistics, biggest_wins, best_records, list_competitions) / ~5 public library entry points.
- **Notable:** Clean layered design (transport → tools → query → graph → models) with immutable records; substantial attention to Brazilian-club name normalization (alias table, accent + state-suffix stripping) and multi-format date/CSV handling. Standings, records, and stats are all computed live from match results.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
