# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/book_api/core.clj | HTTP server, routing, JSON encoding, request validation | `make-app`, `-main` |
| src/book_api/db.clj | SQLite persistence via raw JDBC | `init!`, `create!`, `list-books`, `get-book`, `update!`, `delete!` |
| test/book_api/core_test.clj | Ring handler integration tests over temp SQLite files | 5 `deftest` (book-lifecycle, listing-and-author-filter, validates-create-and-update, database-persists-across-app-instances, health-and-routing) |
| project.clj | Leiningen project: deps (ring-jetty, cheshire, sqlite-jdbc), `:main`, uberjar profile | — |
| README.md | Setup/run/test/build instructions and API table | — |
