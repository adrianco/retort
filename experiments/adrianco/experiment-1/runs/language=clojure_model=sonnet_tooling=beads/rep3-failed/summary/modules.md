# Modules

## Source Files

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/book_api/core.clj | HTTP server setup and route definitions | `app` (Ring handler), `-main` (Jetty startup) |
| src/book_api/handlers.clj | HTTP request handlers for all 6 REST operations | `health-handler`, `create-book-handler`, `list-books-handler`, `get-book-handler`, `update-book-handler`, `delete-book-handler` |
| src/book_api/db.clj | SQLite database abstraction and CRUD operations | `init-db!`, `create-book!`, `list-books`, `get-book`, `update-book!`, `delete-book!` |
| test/book_api/core_test.clj | Integration tests using Ring mock requests | 8 test fixtures: `health-check-test`, `create-book-validation-test`, `create-and-get-book-test`, `list-books-test`, `filter-books-test`, `update-book-test`, `delete-book-test`, `get-nonexistent-book-test` |
| deps.edn | Dependency manifest and build/test aliases | `:test` alias runs cognitect-labs/test-runner, `:run` alias starts the server |

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| org.clojure/clojure | 1.11.1 | Core language |
| ring/ring-core | 1.11.0 | HTTP abstraction layer |
| ring/ring-jetty-adapter | 1.11.0 | Embedded web server |
| metosin/reitit | 0.7.0 | Routing library |
| metosin/reitit-ring | 0.7.0 | Ring-compatible routing |
| metosin/muuntaja | 0.6.10 | JSON/content negotiation middleware |
| metosin/reitit-middleware | 0.7.0 | Reitit middleware utilities |
| com.github.seancorfield/next.jdbc | 1.3.894 | Database abstraction |
| org.xerial/sqlite-jdbc | 3.45.1.0 | SQLite JDBC driver |
| org.clojure/data.json | 2.4.0 | JSON encoding/decoding |
| (test) ring/ring-mock | 0.4.0 | Mock request utilities for testing |
