# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/book_api/core.clj | HTTP server setup and route definitions | `app-routes`, `app`, `-main` |
| src/book_api/handlers.clj | Request handlers and JSON response formatting | `health-handler`, `create-book-handler`, `list-books-handler`, `get-book-handler`, `update-book-handler`, `delete-book-handler`, `json-response` |
| src/book_api/db.clj | SQLite connection management and query execution | `init-db!`, `create-book!`, `get-books`, `get-book`, `update-book!`, `delete-book!`, `get-ds` |
| test/book_api/core_test.clj | Integration tests for all API endpoints and edge cases | 13 test functions covering CRUD operations, validation, filtering, and error conditions |
