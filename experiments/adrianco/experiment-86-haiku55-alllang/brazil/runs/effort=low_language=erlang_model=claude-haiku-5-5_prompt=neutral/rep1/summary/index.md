# Summary: effort=low language=erlang model=claude-haiku-5-5 prompt=neutral · rep 1

- **Shape:** Erlang/OTP MCP server (JSON-RPC 2.0 over stdio) using the built-in `json` module, serving Brazilian soccer queries from 6 Kaggle CSVs loaded into memory.
- **Structure:** 7 source modules + app.src, 5 test files (28 test functions), built with rebar3 (escript).
- **Interfaces:** 5 MCP protocol methods, 8 MCP tools (search_matches, team_record, head_to_head, standings, league_summary, biggest_wins, search_players, club_summary).
- **Notable:** Hand-written RFC-4180 CSV parser and accent-folding tokenizer (no external deps); explicit club-name canonicalization table disambiguating Atlético-MG vs Athletico-PR; cross-file dedupe and two-legged cup-final detection; pure query core cleanly separated from the protocol layer. Very idiomatic for a low-effort run.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
