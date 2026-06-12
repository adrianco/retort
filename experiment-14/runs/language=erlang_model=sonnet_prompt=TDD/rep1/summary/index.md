# Summary: language=erlang model=sonnet prompt=TDD · rep 1

- **Shape:** Erlang/OTP MCP server (stdio JSON-RPC 2.0) over Brazilian soccer CSVs, built with rebar3 + jsx, packaged as an escript.
- **Structure:** 9 source modules + 5 EUnit test files (50 test functions, 84 assertions, 0 skipped).
- **Interfaces:** 6 MCP tools (search_matches, team_stats, head_to_head, search_players, competition_standings, biggest_matches); 8 exported query functions; reads 6 Kaggle CSVs.
- **Notable:** Hand-rolled CSV parser (no external CSV dep); pure query layer cleanly separated from protocol/IO; test files carry explicit "TDD Cycle N" comments reflecting the test-first prompt. OTP app/supervisor scaffolding present but unused by the stdio escript path.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
