# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Axum router, handlers, SQLite persistence, validation, error type | `app()`, `AppState`, `Book`, `BookInput`, `ApiError` |
| src/main.rs | Binary entry point: opens DB, binds TCP listener, serves router | `main()` |
| tests/api.rs | HTTP integration tests via `tower::oneshot` against in-memory DB | 8 `#[tokio::test]` functions |
