# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | Binary entry point; opens `books.db` SQLite file and serves on `0.0.0.0:3000` | `main()` |
| src/lib.rs | Builds the axum `Router`, defines `SharedConn`, provides `test_support::test_app()` | `app()`, `SharedConn`, `test_support::test_app()` |
| src/db.rs | SQLite schema init + CRUD queries | `init_db()`, `insert_book()`, `list_books()`, `get_book()`, `update_book()`, `delete_book()` |
| src/handlers.rs | Axum HTTP handlers for all six endpoints | `health`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `ListBooksQuery` |
| src/models.rs | Domain types + input validation | `Book`, `BookInput`, `BookInput::validate()` |
| tests/books_test.rs | Integration tests for the CRUD surface | 12 `#[tokio::test]` functions |
| tests/health_test.rs | Integration test for the health endpoint | 1 `#[tokio::test]` function |
