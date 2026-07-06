# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | App wiring, router construction, server bootstrap, integration tests | `build_app()`, `main()`, 10 `#[tokio::test]` fns |
| src/handlers.rs | Axum route handlers + request-level validation | `health`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `AppState` |
| src/db.rs | SQLite (rusqlite) CRUD + schema init | `init_db`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| src/models.rs | Serde request/response types | `Book`, `CreateBook`, `UpdateBook`, `BookFilter` |
