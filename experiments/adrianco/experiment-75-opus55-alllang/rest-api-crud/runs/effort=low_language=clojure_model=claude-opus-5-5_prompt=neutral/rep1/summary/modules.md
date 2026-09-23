# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books/core.clj | HTTP server, routes, JSON responses, input validation | `app`, `-main`, `json-resp`, `validate`, `with-book-input`, `with-id` |
| src/books/db.clj | SQLite datasource + CRUD queries via next.jdbc | `make-ds`, `list-books`, `get-book`, `create-book!`, `update-book!`, `delete-book!` |
| test/books/core_test.clj | Ring-mock integration tests | `health`, `crud-flow`, `validation`, `author-filter` (4 deftests) |
