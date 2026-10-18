# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books/core.clj | Jetty server entry point; reads PORT/DB_PATH env, opens DB, starts handler | `-main` |
| src/books/db.clj | SQLite persistence via next.jdbc; schema + CRUD queries | `open`, `list-books`, `get-book`, `create-book!`, `update-book!`, `delete-book!` |
| src/books/handler.clj | Ring routing, validation, JSON middleware, HTTP status mapping | `app`, `routes`, `validate` |
| test/books/validation_test.clj | Unit tests for `validate` | 3 deftests |
| test/books/api_test.clj | Integration tests over the full app handler | 8 deftests |
| test/books/test_runner.clj | clojure.test runner with non-zero exit on failure | `-main` |
