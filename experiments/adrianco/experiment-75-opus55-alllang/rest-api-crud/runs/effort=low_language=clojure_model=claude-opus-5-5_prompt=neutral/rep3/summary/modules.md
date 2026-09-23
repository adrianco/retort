# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books/core.clj | Ring/Compojure HTTP server, SQLite persistence, route handlers, validation | `-main`, `app`, `make-db`, `validate` |
| test/books/core_test.clj | Integration tests against the Ring handler with ring-mock + temp SQLite | 4 deftests: `health`, `crud-lifecycle`, `validation`, `list-with-author-filter` |
