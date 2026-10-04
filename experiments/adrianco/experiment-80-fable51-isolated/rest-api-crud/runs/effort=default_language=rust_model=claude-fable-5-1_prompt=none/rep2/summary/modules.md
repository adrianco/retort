# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | HTTP server, route handlers, SQLite persistence, validation, error mapping | `app()`, `init_db()`, `Book`, `AppState`, `ApiError` |
| src/main.rs | Binary entry point — opens the DB, binds the listener, serves with graceful shutdown | `main()` |
| tests/api.rs | Integration tests over an in-memory DB via `tower::oneshot` | 10 `#[tokio::test]` functions |
