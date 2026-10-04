# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | axum router, handlers, SQLite persistence, error/validation types | `app()`, `Db`, `Book`, `BookInput`, `ApiError` |
| src/main.rs | Binary entry point: opens DB, binds TCP, serves with graceful shutdown | `main()` |
| tests/api.rs | Integration tests driving the router against an in-memory DB | 10 test functions |
