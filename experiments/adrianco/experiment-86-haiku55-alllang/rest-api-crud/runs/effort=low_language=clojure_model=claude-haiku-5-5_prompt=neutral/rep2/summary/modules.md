# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/book_api/core.clj | Entry point; reads PORT/DB_PATH env, starts Jetty | `-main` |
| src/book_api/handler.clj | Ring handler, routing, JSON (de)serialization | `make-handler` |
| src/book_api/db.clj | SQLite persistence via next.jdbc; schema bootstrap | `make-datasource`, `create-book!`, `find-book`, `list-books`, `update-book!`, `delete-book!` |
| src/book_api/validation.clj | Input validation and field normalization | `validate-book`, `normalize-book` |
| test/book_api/handler_test.clj | Integration tests driving the handler against a real temp SQLite file | 9 deftests |
| test/book_api/validation_test.clj | Unit tests for validation/normalization | 4 deftests |
| test/book_api/runner.clj | Test runner; non-zero exit on failure | `-main` |
