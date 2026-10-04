# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Axum router, handlers, SQLite persistence, validation, error mapping | `app`, `open_db`, `Book`, `ApiError` |
| src/main.rs | Binary entry: reads env config, opens DB, serves with graceful shutdown | `main` |
| tests/api.rs | In-process integration tests driving the router against `:memory:` SQLite | 7 test functions |
