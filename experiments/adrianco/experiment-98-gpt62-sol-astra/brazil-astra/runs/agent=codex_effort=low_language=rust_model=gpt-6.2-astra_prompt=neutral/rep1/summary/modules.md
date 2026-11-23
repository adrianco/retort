# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.rs | MCP stdio JSON-RPC server: protocol dispatch, read-only SQL query tool, SQLite authorizer sandbox | `main()`, `rpc()`, `query()`, `secure()`, `DESCRIPTION` |
| data.rs | CSV ingestion into in-memory SQLite; team-name/date normalization; fixture reconciliation across the 5 match files + FIFA players; registers `team_key`/`fold` SQL functions | `load()`, `team()`, `fold()`, `rivals()`, `FILES` |
| views.sql | SQL views/migrations: `team_results` (per-side perspective), `standings` (computed table with ranking), cup-final `stage` tagging | `team_results`, `standings` |
| tests.rs | Integration tests: 21 question→SQL→expected scenarios + tool-discovery test | 2 `#[test]` functions |

Lock files (`Cargo.lock`), the task spec, `data/kaggle/*.csv`, and agent logs are excluded.
