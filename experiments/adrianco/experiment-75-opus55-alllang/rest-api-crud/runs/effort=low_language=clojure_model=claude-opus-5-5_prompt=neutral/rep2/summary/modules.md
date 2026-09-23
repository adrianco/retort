# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books/core.clj | Ring/Jetty + Compojure HTTP server, route handlers, SQLite persistence, validation | `-main`, `app`, `make-db`, `validate` |
| test/books/core_test.clj | Ring-mock integration tests over the app handler | 4 deftests: `health-check`, `crud-lifecycle`, `author-filter`, `validation` |
| deps.edn | tools.deps project + `:run`/`:test` aliases | — |
| README.md | Setup, run, and endpoint documentation | — |
