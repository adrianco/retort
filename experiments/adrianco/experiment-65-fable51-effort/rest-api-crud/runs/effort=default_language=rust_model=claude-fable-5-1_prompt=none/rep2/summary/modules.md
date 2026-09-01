# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | Binary entry point: opens DB, binds TCP, serves the router | `main()` |
| src/lib.rs | Library crate: `AppState`, router assembly | `AppState`, `app()` |
| src/models.rs | Domain types and request validation | `Book`, `BookInput`, `ValidBook`, `ListQuery` |
| src/db.rs | SQLite persistence layer (+ 3 unit tests) | `open`, `init_schema`, `insert`, `list`, `get`, `update`, `delete` |
| src/handlers.rs | Axum HTTP handlers for each route | `health`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| src/error.rs | `ApiError` enum → HTTP status mapping | `ApiError` |
| tests/api.rs | End-to-end integration tests over the router | 7 test functions |
