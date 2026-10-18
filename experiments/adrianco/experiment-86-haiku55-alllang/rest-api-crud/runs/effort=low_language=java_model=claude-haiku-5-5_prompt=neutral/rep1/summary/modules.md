# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/com/example/books/App.java | Process entry point; reads PORT/DB_PATH env, wires repository + server, installs shutdown hook | `App.main` |
| src/main/java/com/example/books/BookServer.java | HTTP layer on JDK `HttpServer`; routing, request parsing, JSON responses | `BookServer(port, repo)`, `start`, `stop`, `port` |
| src/main/java/com/example/books/BookRepository.java | SQLite-backed storage (JDBC); schema create + CRUD + ping | `create`, `findById`, `findAll`, `update`, `delete`, `ping`, `close` |
| src/main/java/com/example/books/Book.java | Immutable book record returned by the API | `Book` (record) |
| src/main/java/com/example/books/BookInput.java | Request-body record with field validation | `BookInput` (record), `validate` |
| src/test/java/com/example/books/BookApiTest.java | End-to-end integration tests over a live server + temp SQLite DB | 6 `@Test` methods |
