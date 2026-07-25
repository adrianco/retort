# Summary: language=erlang model=claude-fable-5 prompt=neutral · rep 1

- **Shape:** Erlang/OTP escript MCP server (JSON-RPC 2.0 over stdio) answering Brazilian-soccer queries, backed by six Kaggle CSVs loaded into ETS.
- **Structure:** 9 source modules + app.src, 4 EUnit test files (~24 test functions).
- **Interfaces:** 6 JSON-RPC methods + 8 MCP tools (search_matches, team_stats, head_to_head, competition_standings, search_players, league_stats, biggest_wins, data_summary); no HTTP or CLI subcommands.
- **Notable:** Clean layered split (transport / rpc / tools / query / data / names / csv / format); hand-written RFC-4180 CSV parser and NFD-based accent-folding team-name normalizer with an alias table; cross-source match de-duplication on a ±1-day canonical team-pair key; long-lived ETS holder process; no external deps beyond kernel/stdlib. Scores: code_quality 1.0, test_coverage 1.0, defect_rate 1.0, idiomatic 0.8, token_efficiency 0.0.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
