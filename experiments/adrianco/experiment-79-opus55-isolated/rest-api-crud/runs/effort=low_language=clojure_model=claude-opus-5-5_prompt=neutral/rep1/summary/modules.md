# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books/core.clj | Ring/Compojure HTTP server, route handlers, validation, JSON responses | `app`, `-main`, `validate` |
| src/books/db.clj | SQLite persistence via next.jdbc (schema + CRUD) | `datasource`, `init!`, `create-book!`, `list-books`, `get-book`, `update-book!`, `delete-book!` |
| test/books/core_test.clj | Full-handler integration tests against a temp SQLite DB | 10 deftest functions |
