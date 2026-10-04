# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib.rs | Axum router, SQLite-backed CRUD handlers, error/validation types | `app()`, `Book`, handlers `health`/`list_books`/`create_book`/`get_book`/`update_book`/`delete_book` |
| main.rs | Binary entry point: opens SQLite, binds TCP, serves with graceful shutdown | `main()` |
| tests.rs | Integration tests driving the router via `tower::oneshot` | 6 `#[tokio::test]` functions |
