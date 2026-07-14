# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | Binary entry point; builds pool, binds TCP listener, serves router | `main()` |
| src/lib.rs | Library root; wires routes to handlers | `app(pool)` |
| src/db.rs | SQLite connection pool + schema bootstrap | `Pool`, `init_pool()` |
| src/models.rs | Book domain type, request payload, validation | `Book`, `BookInput`, `BookInput::validate()` |
| src/handlers.rs | Async axum route handlers (CRUD + health) | `health`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| src/error.rs | Error enum + HTTP status mapping | `AppError`, `IntoResponse` impl |
| tests/books_api.rs | BDD-style integration tests over the router | 11 test functions |
