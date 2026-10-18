# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books/core.clj | Entry point; reads PORT/DB_PATH env, opens datasource, starts Jetty | `-main` |
| src/books/handler.clj | Routing, JSON parsing, validation, response building | `app`, `validation-errors` |
| src/books/db.clj | SQLite access via next.jdbc; schema + CRUD queries | `datasource`, `create-book!`, `get-book`, `list-books`, `update-book!`, `delete-book!` |
| test/books/api_test.clj | Integration tests through the Ring handler against a temp SQLite file | 7 `deftest` functions |
| test/books/runner.clj | Test runner used by `clojure -M:test`; exits non-zero on failure | `-main` |
