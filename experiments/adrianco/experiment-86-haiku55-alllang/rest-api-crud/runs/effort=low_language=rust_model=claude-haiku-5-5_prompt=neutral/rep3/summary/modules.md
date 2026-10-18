# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | HTTP layer: router, handlers, `ApiError` -> JSON mapping | `app()`, `ApiError`, `ListQuery` |
| src/book.rs | Book model, input validation, SQLite persistence | `Book`, `BookInput::validate`, `NewBook`, `init_schema`, `insert`, `get`, `list`, `update`, `delete` |
| src/main.rs | Binary entry point: opens DB, binds port, serves | `main()` |
| tests/api.rs | Black-box HTTP integration tests via `tower::oneshot` | 9 `#[tokio::test]` functions |
