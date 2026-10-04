# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib.rs | Axum router, handlers, SQLite access, validation, error mapping | `app()`, `Book`, `create`, `list`, `fetch`, `update`, `delete` |
| main.rs | Binary entry point; opens SQLite, binds TCP, serves with graceful shutdown | `main()` |
| tests.rs | Integration tests exercising the HTTP router with in-memory/file SQLite | 5 `#[tokio::test]` functions |
