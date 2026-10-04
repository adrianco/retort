# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Library crate: axum router, all route handlers, SQLite access, validation, error type | `Book`, `BookInput`, `ListParams`, `ApiError`, `open_db()`, `app()` |
| src/main.rs | Binary entry point: opens DB, binds TCP listener, serves the router | `main()` |
| tests/api.rs | Integration tests driving the router against an in-memory DB via `tower::oneshot` | 8 `#[tokio::test]` functions |
