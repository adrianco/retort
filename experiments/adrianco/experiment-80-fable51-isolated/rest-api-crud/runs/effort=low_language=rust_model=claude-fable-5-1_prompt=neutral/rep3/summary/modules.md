# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Axum app: router, handlers, SQLite access, validation, error mapping | `Book`, `BookInput`, `ApiError`, `open_db()`, `app()` |
| src/main.rs | Binary entry point: opens DB, binds TCP listener, serves the app | `main()` |
| tests/api.rs | Integration tests against an in-memory SQLite app | 7 test functions |
