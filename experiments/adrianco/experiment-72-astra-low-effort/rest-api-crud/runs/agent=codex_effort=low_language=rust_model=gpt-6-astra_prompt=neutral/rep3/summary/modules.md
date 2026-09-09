# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib.rs | Axum router, SQLite-backed handlers, validation, error type | `app()`, `Database`, `Book` |
| main.rs | Binary entry point: opens DB, binds TCP, serves with graceful shutdown | `main()` |
| tests.rs | Integration tests exercising the router via `oneshot` | 5 `#[tokio::test]` functions |
