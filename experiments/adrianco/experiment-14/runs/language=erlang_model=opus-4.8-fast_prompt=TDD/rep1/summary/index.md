# Summary: language=erlang model=opus-4.8-fast prompt=TDD · rep 1

- **Shape:** Erlang/OTP MCP server (JSON-RPC 2.0 over stdio) answering Brazilian-soccer queries over Kaggle CSVs, zero external deps (uses OTP 27 `json`).
- **Structure:** 10 source modules + 9 test modules, 105 eunit tests (no skips).
- **Interfaces:** 6 MCP tools (find_matches, head_to_head, team_record, find_players, standings, match_statistics); 5 RPC methods; loads 6 datasets.
- **Notable:** Clean layering (transport → protocol → tools → pure query → format); precomputed normalized team keys handle suffix/accent variants; standings/records computed from match data; tool crashes isolated via `safe_call`. Strong TDD signature — fine-grained tests per module.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
