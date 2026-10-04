# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | axum router, SQLite-backed state, handlers, error type | `app`, `AppState`, `AppState::open`, `Book`, `ApiError` |
| src/main.rs | Binary entry: opens DB, binds TCP, serves with graceful shutdown | `main` |
| tests/api.rs | In-process integration tests against `:memory:` DB | 9 test functions |
