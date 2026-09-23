# Architecture summary

Two-file Java service (263 LOC total), no framework beyond the JDK.

- `src/main/java/books/BookServer.java` (183 LOC) — the whole service.
  - Transport: JDK built-in `com.sun.net.httpserver.HttpServer` on `PORT` (default 8080).
  - Persistence: SQLite via `sqlite-jdbc` (`DB_PATH`, default `books.db`); table created on boot.
  - JSON: Jackson `ObjectMapper` for request/response bodies.
  - Two contexts: `/health` and `/books` (the latter dispatches `/books` and `/books/{id}`
    by method in `route()`).
  - Helpers: `validate()` (title/author required, year integer), `bind()`, `row()`, `find()`,
    `list(author)`, `create()`, `update()`. Central `handle()` maps exceptions →
    400 (bad JSON) / 500 and sets `Content-Type: application/json`.
- `src/test/java/books/BookServerTest.java` (80 LOC) — 4 JUnit 5 integration tests driving a
  real in-memory (`jdbc:sqlite::memory:`) server over `java.net.http.HttpClient`.

Flow: request → context handler → `route()` (synchronized, single shared `Connection`) →
prepared statement → `Resp(status, body)` → `handle()` serializes JSON and writes the response.
